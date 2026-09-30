"""Deterministic concept resolution (ADR-0029 item 7).

A small curated registry maps names, import roots, package names and usage calls to one canonical
concept (``XGBoost`` / ``xgboost`` / ``XGBClassifier`` → ``ml.xgboost``). A label that matches no
registry entry becomes its own normalised ``label:<text>`` concept, so identical card titles in
different notebooks still aggregate. Resolution is a projection and never changes a record.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

__all__ = ["CONCEPTS", "Concept", "concept_by_id", "is_placeholder", "is_structural", "label_concept", "normalize",
           "resolve_label", "resolve_text"]

MAX_NGRAM = 4
LABEL_KEY_CHARS = 64
_CJK = re.compile(r"[㐀-鿿豈-﫿]")
_SEPARATOR = re.compile(r"[^\w㐀-鿿豈-﫿]+")
_SCRIPT_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[㐀-鿿豈-﫿])|(?<=[㐀-鿿豈-﫿])(?=[a-z0-9])")
_NUMBERING = re.compile(r"(?:\s*\d+|\s+[ivx]+|\s*[一二三四五六七八九十]+)+$")
#: Section headings that name a card's role, not a topic; such a card is about its parent topic.
STRUCTURAL_HEADINGS = frozenset({
    "proof", "proofs", "summary", "example", "examples", "exercise", "exercises", "note", "notes", "definition",
    "definitions", "theorem", "lemma", "corollary", "remark", "remarks", "question", "questions", "answer",
    "answers", "solution", "solutions", "key points", "overview", "introduction", "conclusion", "review",
    "problem", "problems", "problem set", "case", "cases", "method", "methods", "application", "applications", "code",
    "总结", "小结", "要点", "要点总结", "例题", "例子", "例", "举例", "示例", "证明", "定义", "定理", "引理", "推论",
    "注意", "注", "笔记", "习题", "练习", "答案", "解答", "解析", "题目", "单词", "概述", "引言", "结论", "应用",
    "方法", "代码", "好题错题", "错题",
})
PLACEHOLDER_LABELS = frozenset({"(image)", "…"})


@dataclass(frozen=True)
class Concept:
    """One canonical concept. ``calls`` construct or call it; ``operates`` must also appear if set."""

    id: str
    label: str
    aliases: tuple[str, ...]
    imports: tuple[str, ...] = ()
    packages: tuple[str, ...] = ()
    calls: tuple[str, ...] = ()
    operates: tuple[str, ...] = ()
    text: bool = True  # False: a common word (``Flask``) that names this only in code or manifests


_FIT = (r"\.fit\s*\(", r"\.predict(?:_proba)?\s*\(", r"\.train\s*\(")
_SK = ("sklearn",)
CONCEPTS: tuple[Concept, ...] = (
    Concept("ml.xgboost", "XGBoost", ("xgboost", "xgb", "xgbclassifier", "xgbregressor"), ("xgboost",), ("xgboost",),
            (r"\bXGB(?:Classifier|Regressor|Ranker|RFClassifier|RFRegressor)\s*\(", r"\b(?:xgb|xgboost)\.train\s*\(",
             r"\bDMatrix\s*\("), (*_FIT, r"\b(?:xgb|xgboost)\.train\s*\(")),
    Concept("ml.lightgbm", "LightGBM", ("lightgbm", "lgbm", "lgbmclassifier", "lgbmregressor"), ("lightgbm",),
            ("lightgbm",),
            (r"\bLGBM(?:Classifier|Regressor|Ranker)\s*\(", r"\b(?:lgb|lightgbm)\.train\s*\("),
            (*_FIT, r"\b(?:lgb|lightgbm)\.train\s*\(")),
    Concept("ml.catboost", "CatBoost", ("catboost",), ("catboost",), ("catboost",),
            (r"\bCatBoost(?:Classifier|Regressor|Ranker)?\s*\(",), _FIT),
    Concept("ml.scikit_learn", "scikit-learn", ("scikit-learn", "scikit learn", "sklearn"), _SK,
            ("scikit-learn", "sklearn"),
            (r"\btrain_test_split\s*\(", r"\bcross_val(?:idate|_score)\s*\(",
             r"\b(?:Pipeline|GridSearchCV|RandomizedSearchCV|StandardScaler|MinMaxScaler|OneHotEncoder)\s*\(",
             r"\b(?:RandomForest|GradientBoosting|HistGradientBoosting)(?:Classifier|Regressor)\s*\(",
             r"\b(?:LogisticRegression|LinearRegression|Ridge|Lasso|(?:Linear)?SV[CR]|KMeans|PCA)\s*\("),
            (*_FIT, r"\.fit_transform\s*\(")),
    Concept("ml.random_forest", "Random forest", ("random forest", "random forests", "随机森林"), _SK, (),
            (r"\bRandomForest(?:Classifier|Regressor)\s*\(",), _FIT),
    Concept("ml.gradient_boosting", "Gradient boosting", ("gradient boosting", "gbdt", "梯度提升"), _SK, (),
            (r"\b(?:Hist)?GradientBoosting(?:Classifier|Regressor)\s*\(",), _FIT),
    Concept("ml.logistic_regression", "Logistic regression", ("logistic regression", "逻辑回归", "逻辑斯蒂回归"),
            (*_SK, "statsmodels"), (), (r"\bLogisticRegression(?:CV)?\s*\(", r"\bLogit\s*\("),
            (*_FIT, r"\.fit_regularized\s*\(")),
    Concept("ml.linear_regression", "Linear regression", ("linear regression", "ordinary least squares", "线性回归"),
            (*_SK, "statsmodels"), (), (r"\bLinearRegression\s*\(", r"\bOLS\s*\(", r"\bRidge\s*\(", r"\bLasso\s*\("),
            _FIT),
    Concept("ml.svm", "Support vector machine", ("support vector machine", "support vector machines", "svm",
                                                "支持向量机"), _SK, (), (r"\b(?:Linear)?SV[CR]\s*\(",), _FIT),
    Concept("ml.pca", "Principal component analysis", ("principal component analysis", "pca", "主成分分析"), _SK, (),
            (r"\bPCA\s*\(",), (r"\.fit(?:_transform)?\s*\(",)),
    Concept("ml.kmeans", "k-means clustering", ("k-means", "k means", "kmeans", "k均值"), _SK, (),
            (r"\b(?:MiniBatch)?KMeans\s*\(",), (r"\.fit(?:_predict)?\s*\(",)),
    Concept("ml.neural_networks", "Neural networks", ("neural network", "neural networks", "deep learning",
                                                     "神经网络", "深度学习"),
            ("torch", "tensorflow", "keras"), (),
            (r"\bclass\s+\w+\s*\(\s*nn\.Module\s*\)", r"\bnn\.(?:Linear|Conv[123]d|LSTM|GRU)\s*\(",
             r"\b(?:keras\.)?Sequential\s*\(",
             r"\bDense\s*\("), (r"\.backward\s*\(", r"\.fit\s*\(", r"\boptim\.\w+\s*\(", r"\.step\s*\(")),
    Concept("ml.transformers", "Transformer models", ("transformer model", "transformer models", "hugging face",
                                                     "huggingface", "transformers library"),
            ("transformers",), ("transformers",),
            (r"\bAuto(?:Model\w*|Tokenizer)\.from_pretrained\s*\(", r"\bpipeline\s*\("), ()),
    Concept("ml.pytorch", "PyTorch", ("pytorch",), ("torch",), ("torch", "pytorch"),
            (r"\btorch\.(?:tensor|zeros|ones|randn|from_numpy|save|load)\s*\(", r"\bnn\.\w+\s*\("),
            (r"\.backward\s*\(", r"\boptim\.\w+\s*\(", r"\.to\s*\(")),
    Concept("ml.tensorflow", "TensorFlow", ("tensorflow",), ("tensorflow",), ("tensorflow", "tensorflow-cpu"),
            (r"\btf\.[\w.]+\s*\(", r"\bkeras\.[\w.]+\s*\("), ()),
    Concept("ml.keras", "Keras", ("keras",), ("keras",), ("keras",), (r"\bkeras\.\w+\s*\(", r"\bSequential\s*\("),
            (r"\.fit\s*\(", r"\.compile\s*\(")),
    Concept("ml.jax", "JAX", ("jax",), ("jax",), ("jax",), (r"\bjax\.[\w.]+\s*\(", r"\bjnp\.\w+\s*\("), ()),
    Concept("data.pandas", "pandas", ("pandas",), ("pandas",), ("pandas",),
            (r"\bpd\.(?:DataFrame|read_\w+|concat|merge|Series)\s*\(",), ()),
    Concept("data.numpy", "NumPy", ("numpy",), ("numpy",), ("numpy",), (r"\bnp\.\w+\s*\(",), ()),
    Concept("data.scipy", "SciPy", ("scipy",), ("scipy",), ("scipy",), (r"\b(?:stats|optimize|scipy)\.\w+\s*\(",),
            ()),
    Concept("stats.statsmodels", "statsmodels", ("statsmodels",), ("statsmodels",), ("statsmodels",),
            (r"\bsm\.\w+\s*\(", r"\bsmf\.\w+\s*\("), (r"\.fit\s*\(",)),
    Concept("stats.survival_analysis", "Survival analysis", ("survival analysis", "cox regression",
                                                             "kaplan-meier", "生存分析"),
            ("lifelines", "sksurv"), ("lifelines", "scikit-survival"),
            (r"\bCoxPH(?:Fitter|SurvivalAnalysis)\s*\(", r"\bKaplanMeierFitter\s*\("), (r"\.fit\s*\(",)),
    Concept("stats.bayesian_inference", "Bayesian inference", ("bayesian inference", "bayesian statistics",
                                                               "贝叶斯推断", "贝叶斯统计"),
            ("pymc", "pymc3", "numpyro", "stan", "cmdstanpy"), ("pymc", "pymc3", "numpyro", "cmdstanpy"),
            (r"\bpm\.Model\s*\(", r"\bpm\.sample\s*\(", r"\bMCMC\s*\("), ()),
    Concept("viz.matplotlib", "Matplotlib", ("matplotlib",), ("matplotlib",), ("matplotlib",),
            (r"\bplt\.\w+\s*\(",), ()),
    Concept("viz.seaborn", "seaborn", ("seaborn",), ("seaborn",), ("seaborn",), (r"\bsns\.\w+\s*\(",), ()),
    Concept("cv.opencv", "OpenCV", ("opencv",), ("cv2",), ("opencv-python", "opencv-contrib-python"),
            (r"\bcv2\.\w+\s*\(",), ()),
    Concept("graph.networkx", "NetworkX", ("networkx",), ("networkx",), ("networkx",),
            (r"\bnx\.\w+\s*\(",), ()),
    Concept("web.fastapi", "FastAPI", ("fastapi",), ("fastapi",), ("fastapi",), (r"\bFastAPI\s*\(",), ()),
    Concept("web.flask", "Flask", ("flask",), ("flask",), ("flask",), (r"\bFlask\s*\(",), (), False),
    Concept("web.django", "Django", ("django",), ("django",), ("django",),
            (r"\bclass\s+\w+\s*\(\s*models\.Model\s*\)", r"\bpath\s*\("), ()),
    Concept("py.pydantic", "Pydantic", ("pydantic",), ("pydantic",), ("pydantic",),
            (r"\bclass\s+\w+\s*\(\s*BaseModel\s*\)",), ()),
    Concept("py.pytest", "pytest", ("pytest",), ("pytest",), ("pytest",), (r"\bdef test_\w+\s*\(",), ()),
    Concept("db.sqlite", "SQLite", ("sqlite",), ("sqlite3",), (), (r"\bsqlite3\.connect\s*\(",), ()),
    Concept("js.react", "React", ("react",), ("react",), ("react",), (r"\buse(?:State|Effect)\s*\(",
                                                                          r"<[A-Z]\w*[\s/>]"), (), False),
)


def normalize(text: str) -> str:
    """NFKC, case-folded, punctuation to spaces; CJK characters are kept."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    spaced = _SCRIPT_BOUNDARY.sub(" ", _SEPARATOR.sub(" ", folded).replace("_", " "))
    return " ".join(spaced.split())


def is_placeholder(label: str) -> bool:
    """MarginNote's stand-in for an untitled image or empty card names no topic."""
    return not normalize(label) or " ".join(label.split()) in PLACEHOLDER_LABELS


def is_structural(label: str) -> bool:
    """A heading such as ``Proof``, ``EXAMPLE 2`` or ``总结``: the card's role, not its topic."""
    normal = _NUMBERING.sub("", normalize(label)).strip()
    return normal in STRUCTURAL_HEADINGS


@lru_cache(maxsize=1)
def _index() -> tuple[dict[str, tuple[str, ...]], tuple[tuple[str, str], ...], dict[str, Concept]]:
    words: dict[str, list[str]] = {}
    cjk: list[tuple[str, str]] = []
    for concept in (c for c in CONCEPTS if c.text):
        for alias in (concept.label, *concept.aliases):
            key = normalize(alias)
            if _CJK.search(key):
                cjk.append((key.replace(" ", ""), concept.id))
            elif key:
                words.setdefault(key, [])
                if concept.id not in words[key]:
                    words[key].append(concept.id)
    return ({key: tuple(ids) for key, ids in words.items()}, tuple(cjk), {c.id: c for c in CONCEPTS})


def concept_by_id(concept_id: str) -> Concept | None:
    return _index()[2].get(concept_id)


def resolve_text(text: str) -> tuple[str, ...]:
    """Registry concepts named anywhere in ``text`` (word n-grams, or CJK substrings), in order."""
    words, cjk, _ = _index()
    normal = normalize(text)
    tokens = normal.split()
    found: list[str] = []
    for start in range(len(tokens)):
        for size in range(min(MAX_NGRAM, len(tokens) - start), 0, -1):
            for concept_id in words.get(" ".join(tokens[start:start + size]), ()):
                if concept_id not in found:
                    found.append(concept_id)
    compact = normal.replace(" ", "")
    found.extend(cid for key, cid in cjk if key in compact and cid not in found)
    return tuple(found)


def label_concept(label: str) -> tuple[str, str] | None:
    """The fallback ``label:<text>`` concept id and its display label, or None for an empty label."""
    key = normalize(label)[:LABEL_KEY_CHARS].rstrip()
    return (f"label:{key}", " ".join(label.split())[:LABEL_KEY_CHARS]) if key else None


def resolve_label(label: str) -> tuple[tuple[str, str], ...]:
    """Concepts one card or topic label is about: registry matches, else the label itself."""
    registry = resolve_text(label)
    if registry:
        return tuple((cid, _index()[2][cid].label) for cid in registry)
    fallback = label_concept(label)
    return (fallback,) if fallback else ()
