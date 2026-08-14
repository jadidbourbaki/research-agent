"""The research problem: two capabilities' data, the low- and high-coupling
questions asked against each, and the retrieval functions the agent uses to
read them. lookup is prose documents searched by keyword; metrics is a
structured revenue table queried by company.

The world is synthetic on purpose. The entities do not exist outside this
data, so the agent cannot answer from prior knowledge and must actually
retrieve and, for high-coupling questions, combine facts. That keeps the two
modes comparable and the grading deterministic.
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

# The second capability: a structured table instead of prose documents, so its
# footprint and interface shape genuinely differ from search_documents rather
# than just reusing it over different content. Figures are in $ millions,
# chosen so exactly one company has the largest percentage increase.
REVENUE: dict[str, dict[int, int]] = {
    "Aurelia Systems": {2022: 42, 2023: 58},
    "Brightforge Labs": {2022: 31, 2023: 29},
    "Cindermill Group": {2022: 20, 2023: 33},
    "Delphine Works": {2022: 47, 2023: 51},
}


@dataclass(frozen=True)
class Question:
    id: str
    capability: str
    coupling: str
    hops: int
    prompt: str
    answer: str


QUESTIONS: list[Question] = [
    Question("q1", "lookup", "low", 1, "Who founded Cindermill Group?", "Priya Anand"),
    Question(
        "q2",
        "lookup",
        "low",
        1,
        "What product does Brightforge Labs produce?",
        "Kindle furnace",
    ),
    Question(
        "q3",
        "lookup",
        "high",
        2,
        "In which country is Brightforge Labs headquartered?",
        "Marria",
    ),
    Question(
        "q4",
        "lookup",
        "high",
        2,
        "What product is made by the company headquartered in Torvane?",
        "Vane turbine",
    ),
    Question(
        "q5",
        "lookup",
        "high",
        3,
        "What is the capital of the country where Aurelia Systems is headquartered?",
        "Halden",
    ),
    Question(
        "q6",
        "lookup",
        "high",
        3,
        "In which country is the headquarters of the company founded by Priya Anand?",
        "Sefland",
    ),
    Question(
        "m1",
        "metrics",
        "low",
        1,
        "What was Cindermill Group's revenue in 2023?",
        "33 million",
    ),
    Question(
        "m2",
        "metrics",
        "high",
        4,
        "Which company had the largest percentage increase in revenue from 2022 to 2023?",
        "Cindermill Group",
    ),
]

# The four representative tasks for the paper's Phase 0 pilot: one low- and
# one high-coupling task per capability.
PILOT_QUESTION_IDS: tuple[str, ...] = ("q1", "q5", "m1", "m2")


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


def _format_revenue_row(name: str, figures: dict[int, int]) -> str:
    years = ", ".join(
        f"{year}: ${amount} million" for year, amount in sorted(figures.items())
    )
    return f"{name} revenue by year -> {years}"


def query_revenue(company: str) -> str:
    """Return one company's revenue rows, or every row if none match.

    Matching is case-insensitive substring containment against company names,
    the same style as search_documents.
    """
    needle = company.strip().lower()
    match = next((name for name in REVENUE if needle and needle in name.lower()), None)
    if match is None:
        return "\n".join(
            _format_revenue_row(name, figures) for name, figures in REVENUE.items()
        )
    return _format_revenue_row(match, REVENUE[match])


def pilot_questions() -> list[Question]:
    """The four representative tasks for the Phase 0 pilot cell design."""
    by_id = {q.id: q for q in QUESTIONS}
    return [by_id[qid] for qid in PILOT_QUESTION_IDS]


def is_correct(answer: str, expected: str) -> bool:
    """Grade an answer by normalized containment of the expected string."""
    return expected.strip().lower() in answer.strip().lower()
