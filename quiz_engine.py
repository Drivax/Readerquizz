"""Core quiz logic for Readerquizz.

This module contains no Streamlit UI code.
It focuses only on quiz data structures and game behavior.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, TypedDict


AUTHORS = ["Dostoevsky", "Gogol", "Goncharov", "Tolstoy"]


class ExcerptRecord(TypedDict):
    """A preprocessed quiz excerpt with metadata."""

    excerpt: str
    book: str


@dataclass(frozen=True)
class QuizRound:
    """Represents one quiz round."""

    excerpt: str
    book: str
    correct_author: str
    options: List[str]


def _build_round(corpus: Dict[str, List[ExcerptRecord]], rng: random.Random) -> QuizRound:
    """Create a single randomized round from the corpus."""
    correct_author = rng.choice(AUTHORS)
    record = rng.choice(corpus[correct_author])

    options = AUTHORS[:]
    rng.shuffle(options)
    return QuizRound(
        excerpt=record["excerpt"],
        book=record["book"],
        correct_author=correct_author,
        options=options,
    )


def create_quiz(
    corpus: Dict[str, List[ExcerptRecord]], num_rounds: int = 10, seed: int | None = None
) -> List[QuizRound]:
    """Create a fixed-size quiz of randomized rounds."""
    if num_rounds <= 0:
        raise ValueError("num_rounds must be positive")

    for author in AUTHORS:
        if author not in corpus:
            raise KeyError(f"Missing author in corpus: {author}")
        if not corpus[author]:
            raise ValueError(f"Corpus has no excerpts for: {author}")

    rng = random.Random(seed)
    return [_build_round(corpus, rng) for _ in range(num_rounds)]


def check_answer(round_data: QuizRound, selected_author: str) -> bool:
    """Return True when the selected author is correct."""
    return selected_author == round_data.correct_author


def score_comment(score: int, total: int = 10) -> str:
    """Return a short, encouraging summary based on the final score."""
    if total <= 0:
        return "A fresh literary journey awaits."

    ratio = score / total
    if ratio >= 0.9:
        return "Excellent literary ear. You read style like a critic."
    if ratio >= 0.7:
        return "Strong intuition for Russian prose voices."
    if ratio >= 0.5:
        return "Solid reading instincts. A little more practice will sharpen them."
    if ratio >= 0.3:
        return "Promising start. Keep reading and the signatures become clearer."
    return "Every classic reader starts somewhere. Try another round and trust your ear."