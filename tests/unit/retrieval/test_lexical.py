"""Selected S03 bilingual lexical normalization promoted into production."""

from aptuni.retrieval.lexical import cjk_lexemes, query_expression


def test_lexemes_are_deterministic_and_cover_two_to_four_character_cjk_windows() -> None:
    expected = ["生存", "存分", "分析", "生存分", "存分析", "生存分析", "kkt", "条件"]
    assert cjk_lexemes("生存分析 KKT条件") == expected
    assert cjk_lexemes("生存分析 KKT条件") == expected


def test_query_expression_quotes_terms_and_treats_fts_syntax_as_data() -> None:
    assert query_expression('Cox "hazards"') == '"cox" AND "hazards"'
    assert query_expression('" OR NOT * : ^') == '"or" AND "not"'
