"""The research problem: a fixed document collection, the multi-hop questions
asked against it, and the search tool the agent uses to read it.

The world is synthetic on purpose. The entities do not exist outside these
documents, so the agent cannot answer from prior knowledge and must actually
retrieve and chain facts. That keeps the two modes comparable and the grading
deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DOCUMENTS: dict[str, str] = {
    "founders.md": (
        "Aurelia Systems was founded by Mara Volkov. "
        "Brightforge Labs was founded by Tobias Renn. "
        "Cindermill Group was founded by Priya Anand. "
        "Delphine Works was founded by Owen Marsh."
    ),
    "headquarters.md": (
        "Aurelia Systems is headquartered in the city of Vellmar. "
        "Brightforge Labs is headquartered in Kesselby. "
        "Cindermill Group is headquartered in Torvane. "
        "Delphine Works is headquartered in Vellmar."
    ),
    "geography.md": (
        "The city of Vellmar lies in the country of Norlund. "
        "Kesselby is a city in Marria. "
        "Torvane is located in Sefland."
    ),
    "capitals.md": (
        "The capital of Norlund is Halden. "
        "The capital city of Marria is Quessa. "
        "The capital of Sefland is Dromm."
    ),
    "products.md": (
        "Aurelia Systems makes the Orbit router. "
        "Brightforge Labs produces the Kindle furnace. "
        "Cindermill Group sells the Vane turbine. "
        "Delphine Works builds the Marsh loom."
    ),
}


@dataclass(frozen=True)
class Question:
    id: str
    hops: int
    prompt: str
    answer: str


QUESTIONS: list[Question] = [
    Question("q1", 1, "Who founded Cindermill Group?", "Priya Anand"),
    Question("q2", 1, "What product does Brightforge Labs produce?", "Kindle furnace"),
    Question("q3", 2, "In which country is Brightforge Labs headquartered?", "Marria"),
    Question(
        "q4",
        2,
        "What product is made by the company headquartered in Torvane?",
        "Vane turbine",
    ),
    Question(
        "q5",
        3,
        "What is the capital of the country where Aurelia Systems is headquartered?",
        "Halden",
    ),
    Question(
        "q6",
        3,
        "In which country is the headquarters of the company founded by Priya Anand?",
        "Sefland",
    ),
]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def search_documents(query: str, limit: int = 2) -> str:
    """Return the documents that best match the query, with their full text.

    Scoring is a plain keyword overlap. The collection is tiny, so the ranking
    only needs to surface the right one or two documents.
    """
    query_words = set(_tokens(query))
    scored: list[tuple[int, str, str]] = []
    for name, text in DOCUMENTS.items():
        score = len(query_words & set(_tokens(text)))
        if score:
            scored.append((score, name, text))

    scored.sort(key=lambda entry: entry[0], reverse=True)
    top = scored[:limit]
    if not top:
        return "No matching documents found."
    return "\n\n".join(f"[{name}]\n{text}" for _, name, text in top)


def is_correct(answer: str, expected: str) -> bool:
    """Grade an answer by normalized containment of the expected string."""
    return expected.strip().lower() in answer.strip().lower()
