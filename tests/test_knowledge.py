"""Coverage for the deterministic pieces: search, grading, and question set
integrity. Nothing here calls the live API."""

from __future__ import annotations

from zaki_agent import knowledge
from zaki_agent.knowledge import DOCUMENTS, PILOT_QUESTION_IDS, QUESTIONS, REVENUE


def test_search_returns_the_relevant_document() -> None:
    result = knowledge.search_documents("Brightforge headquarters city")
    assert "headquarters.md" in result
    assert "Kesselby" in result


def test_search_reports_no_match_for_unknown_terms() -> None:
    assert knowledge.search_documents("zzzz qqqq") == "No matching documents found."


def test_search_respects_the_limit() -> None:
    result = knowledge.search_documents("Aurelia Brightforge Cindermill Delphine")
    assert result.count("[") <= 2


def test_query_revenue_returns_the_matching_company_row() -> None:
    result = knowledge.query_revenue("Cindermill")
    assert "Cindermill Group" in result
    assert "33 million" in result
    assert "Aurelia" not in result


def test_query_revenue_is_case_insensitive() -> None:
    assert "Cindermill Group" in knowledge.query_revenue("cindermill group")


def test_query_revenue_returns_every_row_when_nothing_matches() -> None:
    result = knowledge.query_revenue("")
    for name in REVENUE:
        assert name in result


def test_grading_is_case_insensitive_containment() -> None:
    assert knowledge.is_correct("The answer is Marria.", "Marria")
    assert knowledge.is_correct("marria", "Marria")
    assert not knowledge.is_correct("Norlund", "Marria")


def test_every_lookup_answer_is_supported_by_the_documents() -> None:
    corpus = " ".join(DOCUMENTS.values()).lower()
    for question in QUESTIONS:
        if question.capability != "lookup":
            continue
        assert question.answer.lower() in corpus, question.id


def test_every_metrics_answer_is_supported_by_the_revenue_table() -> None:
    corpus = knowledge.query_revenue("").lower()
    for question in QUESTIONS:
        if question.capability != "metrics":
            continue
        assert question.answer.lower() in corpus, question.id


def test_question_ids_are_unique() -> None:
    ids = [q.id for q in QUESTIONS]
    assert len(ids) == len(set(ids))


def test_question_capabilities_and_coupling_are_known() -> None:
    for question in QUESTIONS:
        assert question.capability in {"lookup", "metrics"}, question.id
        assert question.coupling in {"low", "high"}, question.id


def test_pilot_questions_cover_both_capabilities_and_coupling_levels() -> None:
    pilot = knowledge.pilot_questions()
    assert [q.id for q in pilot] == list(PILOT_QUESTION_IDS)
    cells = {(q.capability, q.coupling) for q in pilot}
    assert cells == {
        ("lookup", "low"),
        ("lookup", "high"),
        ("metrics", "low"),
        ("metrics", "high"),
    }
