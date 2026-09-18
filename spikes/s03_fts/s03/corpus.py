"""Deterministic synthetic bilingual corpus and judged queries for S03 (frozen before comparison).

All text is synthetic and depersonalized. Relevance comes from concept tags assigned at generation
time, never from string matching, so judgments cannot be tuned to a tokenizer.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

# key: (English term, Chinese term, extra English words, extra Chinese words)
TOPICS: dict[str, tuple[str, str, str, str]] = {
    "survival_analysis": ("survival analysis", "生存分析", "censoring and Kaplan-Meier curves", "删失与KM曲线"),
    "cox_model": ("Cox proportional hazards", "比例风险模型", "hazard ratio estimation", "风险比估计"),
    "competing_risks": ("competing risks", "竞争风险", "Fine-Gray subdistribution hazard", "Fine-Gray亚分布风险"),
    "random_forest": ("random forest", "随机森林", "bagging with decision trees", "决策树装袋"),
    "xgboost": ("XGBoost", "XGBoost", "gradient boosted trees", "梯度提升树"),
    "convex_optimization": ("convex optimization", "凸优化", "duality and KKT conditions", "对偶与KKT条件"),
    "probability": ("probability theory", "概率论", "random variables and expectation", "随机变量与期望"),
    "statistical_inference": ("statistical inference", "统计推断", "confidence intervals", "置信区间"),
    "quant_finance": ("quantitative finance", "量化金融", "asset pricing basics", "资产定价基础"),
    "time_series": ("time series", "时间序列", "ARIMA and autocorrelation", "ARIMA与自相关"),
    "machine_learning": ("machine learning", "机器学习", "bias variance trade-off", "偏差方差权衡"),
    "deep_learning": ("deep learning", "深度学习", "backpropagation in neural networks", "神经网络反向传播"),
    "bayesian": ("Bayesian statistics", "贝叶斯统计", "posterior and prior", "后验与先验"),
    "linear_algebra": ("linear algebra", "线性代数", "eigenvalues and matrix factorization", "特征值与矩阵分解"),
    "python": ("Python programming", "Python编程", "pandas and numpy", "pandas与numpy"),
    "databases": ("SQL databases", "数据库", "joins and indexes", "连接与索引"),
    "medical_imaging": ("medical imaging", "医学影像", "CT image preprocessing", "CT图像预处理"),
    "concise_answers": ("concise answers", "简洁回答", "conclusion first", "先给结论"),
    "markdown_format": ("Markdown formatting", "Markdown格式", "math in dollar signs", "公式用美元符号"),
    "portfolio_optimization": ("portfolio optimization", "投资组合优化", "mean variance allocation", "均值方差配置"),
    "hypothesis_testing": ("hypothesis testing", "假设检验", "p-values and power", "p值与检验功效"),
    "causal_inference": ("causal inference", "因果推断", "confounding and propensity scores", "混杂与倾向评分"),
    "reinforcement_learning": ("reinforcement learning", "强化学习", "policy gradient and rewards", "策略梯度与奖励"),
    "volatility": ("volatility modeling", "波动率建模", "GARCH models", "GARCH模型"),
}

EN_TEMPLATES = (
    "Studied {en} with detailed notes on {extra}.",
    "Applied {en} in a course project; wrote about {extra}.",
    "Mind map: {en} — key ideas, worked examples, {extra}.",
    "Wants to deepen {en} next semester, starting from {extra}.",
    "Evidence: chapter summary on {en} including {extra}.",
)
ZH_TEMPLATES = (
    "学过{zh}，笔记里记录了{extra}。",
    "在课程项目中应用了{zh}，并写了{extra}的总结。",
    "思维导图：{zh}的核心概念、例题与{extra}。",
    "下学期想深入{zh}，先从{extra}开始。",
    "证据：{zh}章节总结，包含{extra}。",
)
# Hard negatives: share characters or words with topics but are about something else.
DISTRACTORS = (
    ("en", "Enjoys forest hiking and survival games on weekends."),
    ("en", "Read a news article about venture capital risk appetite."),
    ("en", "Prefers long narrative explanations for history topics."),
    ("zh", "周末喜欢在森林里徒步，也玩生存类游戏。"),
    ("zh", "读了一篇关于风险投资偏好的新闻。"),
    ("zh", "生活中存储了很多照片，需要整理。"),
    ("zh", "喜欢听音乐，偶尔学习做饭。"),
    ("zh", "历史话题更喜欢长篇叙述。"),
    ("zh", "金色的秋天，融化的雪。"),
    ("en", "Organized family photos into albums."),
)


def build_corpus() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for key, (en, zh, en_extra, zh_extra) in TOPICS.items():
        for index, template in enumerate(EN_TEMPLATES):
            docs.append({"id": f"d-{key}-en-{index}", "lang": "en", "tags": [key],
                         "text": template.format(en=en, extra=en_extra)})
        for index, template in enumerate(ZH_TEMPLATES):
            docs.append({"id": f"d-{key}-zh-{index}", "lang": "zh", "tags": [key],
                         "text": template.format(zh=zh, extra=zh_extra)})
    for index, (lang, text) in enumerate(DISTRACTORS):
        docs.append({"id": f"d-distractor-{index}", "lang": lang, "tags": ["distractor"], "text": text})
    return docs


# (query id, text, relevant topics, language scope, kind)
QUERIES: tuple[tuple[str, str, tuple[str, ...], str, str], ...] = (
    ("q-en-survival", "survival analysis", ("survival_analysis",), "en", "en_term"),
    ("q-en-cox", "Cox hazards", ("cox_model",), "en", "en_term"),
    ("q-en-competing", "competing risks", ("competing_risks",), "en", "en_term"),
    ("q-en-forest", "random forest", ("random_forest",), "en", "en_term"),
    ("q-en-xgb", "XGBoost", ("xgboost",), "any", "en_term"),
    ("q-en-convex", "convex optimization", ("convex_optimization",), "en", "en_term"),
    ("q-en-prob", "probability", ("probability",), "en", "en_term"),
    ("q-en-inference", "statistical inference", ("statistical_inference",), "en", "en_term"),
    ("q-en-quant", "quantitative finance", ("quant_finance",), "en", "en_term"),
    ("q-en-ts", "time series ARIMA", ("time_series",), "en", "en_term"),
    ("q-en-ml", "machine learning", ("machine_learning",), "en", "en_term"),
    ("q-en-dl", "neural networks backpropagation", ("deep_learning",), "en", "en_term"),
    ("q-en-bayes", "Bayesian posterior", ("bayesian",), "en", "en_term"),
    ("q-en-linalg", "eigenvalues", ("linear_algebra",), "en", "en_term"),
    ("q-en-pandas", "pandas", ("python",), "any", "en_term"),
    ("q-en-sql", "SQL joins", ("databases",), "en", "en_term"),
    ("q-en-imaging", "medical imaging", ("medical_imaging",), "en", "en_term"),
    ("q-en-concise", "concise answers", ("concise_answers",), "en", "en_term"),
    ("q-en-markdown", "Markdown", ("markdown_format",), "any", "en_term"),
    ("q-en-portfolio", "portfolio optimization", ("portfolio_optimization",), "en", "en_term"),
    ("q-en-hyp", "hypothesis testing", ("hypothesis_testing",), "en", "en_term"),
    ("q-en-causal", "causal inference propensity", ("causal_inference",), "en", "en_term"),
    ("q-en-rl", "reinforcement learning", ("reinforcement_learning",), "en", "en_term"),
    ("q-en-garch", "GARCH volatility", ("volatility",), "en", "en_term"),
    ("q-en-optimization", "optimization", ("convex_optimization", "portfolio_optimization"), "en", "en_term"),
    ("q-zh-survival", "生存分析", ("survival_analysis",), "zh", "zh_long"),
    ("q-zh-cox", "比例风险模型", ("cox_model",), "zh", "zh_long"),
    ("q-zh-competing", "竞争风险", ("competing_risks",), "zh", "zh_long"),
    ("q-zh-forest", "随机森林", ("random_forest",), "zh", "zh_long"),
    ("q-zh-convex", "凸优化", ("convex_optimization",), "zh", "zh_long"),
    ("q-zh-prob", "概率论", ("probability",), "zh", "zh_long"),
    ("q-zh-inference", "统计推断", ("statistical_inference",), "zh", "zh_long"),
    ("q-zh-quant", "量化金融", ("quant_finance",), "zh", "zh_long"),
    ("q-zh-ts", "时间序列", ("time_series",), "zh", "zh_long"),
    ("q-zh-ml", "机器学习", ("machine_learning",), "zh", "zh_long"),
    ("q-zh-dl", "深度学习", ("deep_learning",), "zh", "zh_long"),
    ("q-zh-bayes", "贝叶斯", ("bayesian",), "zh", "zh_long"),
    ("q-zh-linalg", "线性代数", ("linear_algebra",), "zh", "zh_long"),
    ("q-zh-db", "数据库", ("databases",), "zh", "zh_long"),
    ("q-zh-imaging", "医学影像", ("medical_imaging",), "zh", "zh_long"),
    ("q-zh-concise", "简洁回答", ("concise_answers",), "zh", "zh_long"),
    ("q-zh-portfolio", "投资组合优化", ("portfolio_optimization",), "zh", "zh_long"),
    ("q-zh-hyp", "假设检验", ("hypothesis_testing",), "zh", "zh_long"),
    ("q-zh-causal", "因果推断", ("causal_inference",), "zh", "zh_long"),
    ("q-zh-rl", "强化学习", ("reinforcement_learning",), "zh", "zh_long"),
    ("q-zh-vol", "波动率建模", ("volatility",), "zh", "zh_long"),
    ("q-zh2-survival", "生存", ("survival_analysis",), "zh", "zh_two_char"),
    ("q-zh2-forest", "森林", ("random_forest",), "zh", "zh_two_char"),
    ("q-zh2-optim", "优化", ("convex_optimization", "portfolio_optimization"), "zh", "zh_two_char"),
    ("q-zh2-infer", "推断", ("statistical_inference", "causal_inference"), "zh", "zh_two_char"),
    ("q-zh2-finance", "金融", ("quant_finance",), "zh", "zh_two_char"),
    ("q-zh2-seq", "序列", ("time_series",), "zh", "zh_two_char"),
    ("q-zh2-imaging", "影像", ("medical_imaging",), "zh", "zh_two_char"),
    ("q-zh2-test", "检验", ("hypothesis_testing",), "zh", "zh_two_char"),
    ("q-zh2-vol", "波动", ("volatility",), "zh", "zh_two_char"),
    ("q-zh2-algebra", "代数", ("linear_algebra",), "zh", "zh_two_char"),
    ("q-zh2-prob", "概率", ("probability",), "zh", "zh_two_char"),
    ("q-zh2-reward", "奖励", ("reinforcement_learning",), "zh", "zh_two_char"),
    ("q-mix-xgb", "XGBoost 梯度提升", ("xgboost",), "zh", "mixed"),
    ("q-mix-python", "Python编程", ("python",), "zh", "mixed"),
    ("q-mix-md", "Markdown格式", ("markdown_format",), "zh", "mixed"),
    ("q-mix-ct", "CT图像", ("medical_imaging",), "zh", "mixed"),
    ("q-mix-kkt", "KKT条件", ("convex_optimization",), "zh", "mixed"),
    ("q-mix-garch", "GARCH模型", ("volatility",), "zh", "mixed"),
    ("q-mix-finegray", "Fine-Gray", ("competing_risks",), "any", "mixed"),
    ("q-neg-blockchain", "blockchain", (), "any", "negative"),
    ("q-neg-quantum", "quantum computing", (), "any", "negative"),
    ("q-neg-zh-blockchain", "区块链", (), "any", "negative"),
    ("q-neg-zh-topology", "拓扑", (), "any", "negative"),
    ("q-neg-zh-game", "生存游戏攻略", (), "any", "negative"),
    ("q-neg-zh-bio", "生物信息", (), "any", "negative"),
    ("q-neg-zh-gold", "金融危机", (), "any", "negative"),
    ("q-neg-en-hiking", "mountain climbing", (), "any", "negative"),
)


def split_of(query_id: str) -> str:
    """Deterministic ~30% holdout by hash of the query id."""
    return "holdout" if int(hashlib.sha256(query_id.encode()).hexdigest(), 16) % 10 < 3 else "dev"


def build_queries(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queries = []
    for qid, text, topics, scope, kind in QUERIES:
        relevant = sorted(d["id"] for d in docs
                          if set(d["tags"]) & set(topics) and (scope == "any" or d["lang"] == scope))
        queries.append({"id": qid, "text": text, "kind": kind, "split": split_of(qid), "relevant": relevant})
    return queries


def write_frozen(out_dir: Path) -> None:
    docs = build_corpus()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "corpus.jsonl").write_text(
        "".join(json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n" for d in docs), encoding="utf-8")
    (out_dir / "queries.jsonl").write_text(
        "".join(json.dumps(q, ensure_ascii=False, sort_keys=True) + "\n" for q in build_queries(docs)),
        encoding="utf-8")
