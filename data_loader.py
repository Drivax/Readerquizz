"""Data download and preprocessing utilities for Readerquizz.

This module handles:
1. Downloading public domain texts (first run).
2. Storing raw files locally.
3. Cleaning and preprocessing text.
4. Building many two-sentence excerpts per author.
5. Saving/loading processed data for fast subsequent launches.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, TypedDict

import requests

# Core app locations.
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_FILE = PROCESSED_DIR / "quiz_excerpts.json"
MANIFEST_FILE = PROCESSED_DIR / "manifest.json"

# The four required quiz authors.
AUTHORS = ["Dostoevsky", "Gogol", "Goncharov", "Tolstoy"]


class ExcerptRecord(TypedDict):
    """A preprocessed quiz excerpt with source metadata."""

    excerpt: str
    book: str


@dataclass(frozen=True)
class SourceConfig:
    """Represents one book source with fallback URLs."""

    title: str
    urls: List[str]


# Multiple sources per author improve variety and resilience.
AUTHOR_SOURCES: Dict[str, List[SourceConfig]] = {
    "Dostoevsky": [
        SourceConfig(
            title="Crime and Punishment",
            urls=[
                "https://www.gutenberg.org/files/2554/2554-0.txt",
                "https://www.gutenberg.org/cache/epub/2554/pg2554.txt",
            ],
        ),
        SourceConfig(
            title="Notes from Underground",
            urls=[
                "https://www.gutenberg.org/files/600/600-0.txt",
                "https://www.gutenberg.org/cache/epub/600/pg600.txt",
            ],
        ),
    ],
    "Gogol": [
        SourceConfig(
            title="Dead Souls",
            urls=[
                "https://www.gutenberg.org/files/1081/1081-0.txt",
                "https://www.gutenberg.org/cache/epub/1081/pg1081.txt",
            ],
        ),
    ],
    "Goncharov": [
        SourceConfig(
            title="Oblomov",
            urls=[
                "https://www.gutenberg.org/files/54700/54700-0.txt",
                "https://www.gutenberg.org/cache/epub/54700/pg54700.txt",
            ],
        ),
    ],
    "Tolstoy": [
        SourceConfig(
            title="Anna Karenina",
            urls=[
                "https://www.gutenberg.org/files/1399/1399-0.txt",
                "https://www.gutenberg.org/cache/epub/1399/pg1399.txt",
            ],
        ),
        SourceConfig(
            title="War and Peace",
            urls=[
                "https://www.gutenberg.org/files/2600/2600-0.txt",
                "https://www.gutenberg.org/cache/epub/2600/pg2600.txt",
            ],
        ),
    ],
}


def _default_progress_callback(_stage: str, _progress: float, _message: str) -> None:
    """Fallback callback when caller does not provide UI progress handling."""


def _ensure_directories() -> None:
    """Create required data directories if they do not exist."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def _slugify(text: str) -> str:
    """Create filesystem-safe lowercase slug from human-readable title."""
    lowered = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", lowered)
    return slug.strip("_") or "source"


def _download_text_from_sources(author: str, urls: List[str]) -> str:
    """Attempt to download text from a list of candidate URLs.

    Raises:
        RuntimeError: If all URLs fail for the given author.
    """
    headers = {"User-Agent": "Readerquizz/1.0 (educational app)"}
    errors: List[str] = []

    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=45)
            response.raise_for_status()
            text = response.text
            if len(text) < 20_000:
                errors.append(f"{url} -> content too short")
                continue
            return text
        except Exception as exc:  # noqa: BLE001 - keep retries broad and resilient.
            errors.append(f"{url} -> {exc}")

    joined_errors = "\n".join(errors)
    raise RuntimeError(f"Failed to download text for {author}.\n{joined_errors}")


def _strip_gutenberg_boilerplate(text: str) -> str:
    """Remove common Project Gutenberg header/footer markers when present."""
    start_patterns = [
        r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
        r"\*\*\*\s*START OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*",
    ]
    end_patterns = [
        r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
        r"\*\*\*\s*END OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*",
    ]

    start_idx = 0
    end_idx = len(text)

    for pattern in start_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            start_idx = max(start_idx, match.end())

    for pattern in end_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            end_idx = min(end_idx, match.start())

    return text[start_idx:end_idx]


def _clean_text(text: str) -> str:
    """Normalize whitespace and remove obvious non-content artifacts."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _strip_gutenberg_boilerplate(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[_*]{2,}", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _split_into_sentences(text: str) -> List[str]:
    """Split long text into sentence-like units with practical filtering."""
    normalized = re.sub(r"\s+", " ", text)
    raw_sentences = re.split(r"(?<=[.!?…])\s+", normalized)

    cleaned: List[str] = []
    for sentence in raw_sentences:
        candidate = sentence.strip(" \t\n\"“”'[]()")
        if not candidate:
            continue
        if len(candidate) < 35 or len(candidate) > 450:
            continue
        if candidate.count(" ") < 5:
            continue
        cleaned.append(candidate)

    return cleaned


def _build_two_sentence_excerpts(sentences: List[str], max_excerpts: int = 1500) -> List[str]:
    """Build valid two-sentence excerpts from adjacent sentence pairs."""
    excerpts: List[str] = []
    for idx in range(len(sentences) - 1):
        first = sentences[idx].strip()
        second = sentences[idx + 1].strip()
        if not first or not second:
            continue

        excerpt = f"{first} {second}"
        if len(excerpt) < 180 or len(excerpt) > 900:
            continue
        excerpts.append(excerpt)

    if len(excerpts) > max_excerpts:
        rng = random.Random(42)
        excerpts = rng.sample(excerpts, max_excerpts)

    return excerpts


def _normalize_loaded_records(author: str, raw_records: List[object]) -> List[ExcerptRecord]:
    """Normalize old/new processed file formats to the current record schema."""
    normalized: List[ExcerptRecord] = []
    for item in raw_records:
        if isinstance(item, dict) and "excerpt" in item:
            excerpt = str(item["excerpt"]).strip()
            if not excerpt:
                continue
            book = str(item.get("book", f"Collected Works ({author})")).strip() or f"Collected Works ({author})"
            normalized.append({"excerpt": excerpt, "book": book})
        elif isinstance(item, str):
            excerpt = item.strip()
            if excerpt:
                normalized.append({"excerpt": excerpt, "book": f"Collected Works ({author})"})
    return normalized


def _load_processed_file() -> Dict[str, List[ExcerptRecord]]:
    """Load preprocessed excerpts from disk."""
    with PROCESSED_FILE.open("r", encoding="utf-8") as file_obj:
        data = json.load(file_obj)

    loaded: Dict[str, List[ExcerptRecord]] = {}
    for author in AUTHORS:
        loaded[author] = _normalize_loaded_records(author, data.get(author, []))
    return loaded


def _write_processed_files(excerpts_by_author: Dict[str, List[ExcerptRecord]]) -> None:
    """Persist processed excerpts and metadata."""
    payload = {author: excerpts_by_author[author] for author in AUTHORS}
    with PROCESSED_FILE.open("w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, ensure_ascii=False, indent=2)

    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "authors": AUTHORS,
        "source_urls": {
            author: [{"title": source.title, "urls": source.urls} for source in AUTHOR_SOURCES[author]]
            for author in AUTHORS
        },
        "excerpt_counts": {author: len(excerpts_by_author[author]) for author in AUTHORS},
    }
    with MANIFEST_FILE.open("w", encoding="utf-8") as file_obj:
        json.dump(manifest, file_obj, ensure_ascii=False, indent=2)


def ensure_corpus(
    progress_callback: Optional[Callable[[str, float, str], None]] = None,
) -> Dict[str, List[ExcerptRecord]]:
    """Ensure local corpus exists and return excerpts per author.

    If processed data is already present, it is loaded immediately.
    Otherwise the function downloads and preprocesses source texts.
    """
    callback = progress_callback or _default_progress_callback
    _ensure_directories()

    if PROCESSED_FILE.exists():
        callback("load", 1.0, "Using local processed dataset.")
        return _load_processed_file()

    callback("prepare", 0.02, "Preparing first-time corpus download...")
    excerpts_by_author: Dict[str, List[ExcerptRecord]] = {}

    total_authors = len(AUTHORS)
    for index, author in enumerate(AUTHORS, start=1):
        author_base = (index - 1) / total_authors
        callback(
            "download",
            author_base + (0.15 / total_authors),
            f"Downloading texts for {author}...",
        )

        author_records: List[ExcerptRecord] = []
        for source in AUTHOR_SOURCES[author]:
            source_slug = _slugify(source.title)
            raw_path = RAW_DIR / f"{author.lower()}_{source_slug}.txt"
            if raw_path.exists():
                raw_text = raw_path.read_text(encoding="utf-8", errors="ignore")
            else:
                raw_text = _download_text_from_sources(author, source.urls)
                raw_path.write_text(raw_text, encoding="utf-8")

            callback(
                "preprocess",
                author_base + (0.55 / total_authors),
                f"Preprocessing {source.title} ({author})...",
            )
            cleaned = _clean_text(raw_text)
            sentences = _split_into_sentences(cleaned)
            excerpts = _build_two_sentence_excerpts(sentences, max_excerpts=900)

            for excerpt in excerpts:
                author_records.append({"excerpt": excerpt, "book": source.title})

        if len(author_records) < 50:
            raise RuntimeError(
                f"Not enough valid excerpts generated for {author}. "
                "Please verify source URLs in data_loader.py."
            )

        if len(author_records) > 1800:
            rng = random.Random(42)
            author_records = rng.sample(author_records, 1800)

        excerpts_by_author[author] = author_records

        callback(
            "progress",
            index / total_authors,
            f"Prepared {len(author_records)} excerpts for {author}.",
        )

    callback("save", 0.97, "Saving processed dataset...")
    _write_processed_files(excerpts_by_author)
    callback("done", 1.0, "Corpus ready.")

    return excerpts_by_author