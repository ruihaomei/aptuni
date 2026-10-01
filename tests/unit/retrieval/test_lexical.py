"""Selected S03 bilingual lexical normalization promoted into production."""

from aptuni.retrieval.lexical import cjk_lexemes, fallback_expression, query_expression


def test_lexemes_are_deterministic_and_cover_two_to_four_character_cjk_windows() -> None:
    expected = ["生存", "存分", "分析", "生存分", "存分析", "生存分析", "kkt", "条件"]
    assert cjk_lexemes("生存分析 KKT条件") == expected
    assert cjk_lexemes("生存分析 KKT条件") == expected


def test_query_expression_quotes_terms_and_treats_fts_syntax_as_data() -> None:
    assert query_expression('Cox "hazards"') == '"cox" AND "hazards"'
    assert query_expression('" OR NOT * : ^') == '"or" AND "not"'


def test_any_expression_drops_stopwords_and_keeps_data_quoting() -> None:
    assert query_expression("help me prepare for a data science interview", mode="any") == (
        '"prepare" OR "data" OR "science" OR "interview"')
    assert query_expression("教我生存分析", mode="any") is not None
    assert "教我" not in str(query_expression("教我生存分析", mode="any"))
    assert query_expression("the of and", mode="any") is None


def test_fallback_requires_task_language_to_have_been_removed() -> None:
    assert fallback_expression("help me prepare for a data science interview") is not None
    assert fallback_expression("教我生存分析") is not None
    assert fallback_expression("金融危机") is None
    assert fallback_expression("生存游戏攻略") is None


def test_multi_keyword_queries_fall_back_to_whole_keywords_only() -> None:
    # Agent-written keyword lists carry no task language; one absent keyword must not empty them.
    assert fallback_expression("learning transformer") == '"learning" OR "transformer"'
    expression = fallback_expression("职业规划 自学")
    assert expression == '("职业" AND "业规" AND "规划" AND "职业规" AND "业规划" AND "职业规划") OR "自学"'
    # A keyword is never weakened to one of its own fragments.
    assert fallback_expression("金融危机") is None
    assert fallback_expression("learning learning") is None
    # Script changes inside one token do not split a keyword; only spaces and punctuation do.
    assert fallback_expression("Python数据分析") is None
    assert fallback_expression("职业规划、自学") is not None
