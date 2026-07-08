"""Coverage for the deterministic pieces: search, grading, and question set
integrity. Nothing here calls the live API."""

from __future__ import annotations

from zaki_agent import knowledge
from zaki_agent.knowledge import DOCUMENTS, QUESTIONS


def test_search_returns_the_relevant_document() -> None:
    result = knowledge.search_documents("Brightforge headquarters city")
    assert "headquarters.md" in result
    assert "Kesselby" in result


def test_search_reports_no_match_for_unknown_terms() -> None:
    assert knowledge.search_documents("zzzz qqqq") == "No matching documents found."


def test_search_respects_the_limit() -> None:
    result = knowledge.search_documents("Aurelia Brightforge Cindermill Delphine")
    assert result.count("[") <= 2


def test_grading_is_case_insensitive_containment() -> None:
    assert knowledge.is_correct("The answer is Marria.", "Marria")
    assert knowledge.is_correct("marria", "Marria")
    assert not knowledge.is_correct("Norlund", "Marria")


def test_every_answer_is_supported_by_the_documents() -> None:
    corpus = " ".join(DOCUMENTS.values()).lower()
    for question in QUESTIONS:
        assert question.answer.lower() in corpus, question.id


def test_question_ids_are_unique() -> None:
    ids = [q.id for q in QUESTIONS]
    assert len(ids) == len(set(ids))
