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
