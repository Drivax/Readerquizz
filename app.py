"""Readerquizz Streamlit application.

Main responsibilities:
1. Handle app state and navigation.
2. Trigger first-run data preparation with progress feedback.
3. Render quiz rounds, immediate answer feedback, and final results.
"""

from __future__ import annotations

from typing import Dict, List

import streamlit as st

from data_loader import ExcerptRecord, ensure_corpus
from quiz_engine import QuizRound, check_answer, create_quiz, score_comment


TOTAL_ROUNDS = 10


def _configure_page() -> None:
    """Apply page config and custom literary visual theme."""
    st.set_page_config(
        page_title="Readerquizz",
        page_icon="📚",
        layout="centered",
        initial_sidebar_state="collapsed",
    )

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Libre+Baskerville:wght@400;700&display=swap');

        :root {
            --rq-bg-1: #0f1218;
            --rq-bg-2: #1a2230;
            --rq-gold: #c8a96a;
            --rq-ivory: #efe7d6;
            --rq-muted: #b9b0a0;
            --rq-card: rgba(18, 25, 35, 0.74);
            --rq-success: #5aa67a;
            --rq-error: #c06b6b;
        }

        .stApp {
            background:
                radial-gradient(circle at 10% 10%, rgba(200, 169, 106, 0.15), transparent 35%),
                radial-gradient(circle at 90% 85%, rgba(120, 160, 210, 0.14), transparent 35%),
                linear-gradient(140deg, var(--rq-bg-1), var(--rq-bg-2));
        }

        h1, h2, h3 {
            font-family: 'Cormorant Garamond', serif !important;
            letter-spacing: 0.3px;
            color: var(--rq-ivory);
        }

        p, li, span, div {
            font-family: 'Libre Baskerville', serif;
        }

        .rq-card {
            border: 1px solid rgba(200, 169, 106, 0.28);
            border-radius: 14px;
            padding: 1.15rem 1.1rem;
            background: var(--rq-card);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.26);
            margin: 1rem 0;
            animation: rq-fade-in 450ms ease-out;
        }

        .rq-excerpt {
            color: var(--rq-ivory);
            font-size: 1.1rem;
            line-height: 1.7;
        }

        .rq-subtle {
            color: var(--rq-muted);
            font-size: 0.94rem;
        }

        .rq-score {
            color: var(--rq-gold);
            font-size: 1.2rem;
            font-weight: 700;
            letter-spacing: 0.3px;
        }

        @keyframes rq-fade-in {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .stButton > button {
            border-radius: 10px !important;
            border: 1px solid rgba(200, 169, 106, 0.45) !important;
            font-family: 'Libre Baskerville', serif !important;
            transition: transform 120ms ease, box-shadow 120ms ease;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
        }

        .rq-option-state {
            border-radius: 10px;
            padding: 0.62rem 0.7rem;
            margin-top: 0.35rem;
            margin-bottom: 0.2rem;
            font-size: 0.95rem;
            border: 1px solid rgba(200, 169, 106, 0.35);
            background: rgba(255, 255, 255, 0.04);
            color: var(--rq-ivory);
            text-align: center;
        }

        .rq-option-state.correct {
            border-color: rgba(90, 166, 122, 0.8);
            background: rgba(90, 166, 122, 0.22);
        }

        .rq-option-state.wrong {
            border-color: rgba(192, 107, 107, 0.8);
            background: rgba(192, 107, 107, 0.22);
        }

        .rq-option-state.answer {
            border-color: rgba(200, 169, 106, 0.8);
            background: rgba(200, 169, 106, 0.2);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_state() -> None:
    """Initialize Streamlit session state values once."""
    defaults = {
        "view": "home",
        "corpus": None,
        "corpus_ready": False,
        "rounds": [],
        "current_round_idx": 0,
        "score": 0,
        "answered": False,
        "selected_author": None,
        "last_answer_correct": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _prepare_corpus_ui() -> Dict[str, List[ExcerptRecord]]:
    """Load or build corpus with on-screen progress updates."""
    status_text = st.empty()
    progress = st.progress(0)

    def callback(_stage: str, ratio: float, message: str) -> None:
        safe_ratio = max(0.0, min(1.0, ratio))
        progress.progress(safe_ratio)
        status_text.markdown(f"<p class='rq-subtle'>{message}</p>", unsafe_allow_html=True)

    corpus = ensure_corpus(progress_callback=callback)
    progress.progress(1.0)
    status_text.markdown("<p class='rq-subtle'>Corpus ready. You can begin.</p>", unsafe_allow_html=True)
    return corpus


def _start_new_quiz() -> None:
    """Reset game state and generate a new 10-round quiz."""
    rounds = create_quiz(st.session_state["corpus"], num_rounds=TOTAL_ROUNDS)
    st.session_state["rounds"] = rounds
    st.session_state["current_round_idx"] = 0
    st.session_state["score"] = 0
    st.session_state["answered"] = False
    st.session_state["selected_author"] = None
    st.session_state["last_answer_correct"] = None
    st.session_state["view"] = "quiz"


def _go_to_next_round_or_results() -> None:
    """Advance to next round or finish quiz."""
    st.session_state["current_round_idx"] += 1
    st.session_state["answered"] = False
    st.session_state["selected_author"] = None
    st.session_state["last_answer_correct"] = None

    if st.session_state["current_round_idx"] >= TOTAL_ROUNDS:
        st.session_state["view"] = "results"


def _render_home() -> None:
    """Render home screen and first-run data setup."""
    st.title("Readerquizz - Guess the Russian Author")
    st.markdown(
        "<p class='rq-subtle'>Read a two-sentence extract and identify its author. "
        "Ten rounds. Four classics. One literary intuition test.</p>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='rq-card'>", unsafe_allow_html=True)
    st.markdown(
        "<p class='rq-subtle'>"
        "Preparing local corpus (first launch only). Readerquizz downloads and preprocesses "
        "public-domain works for Dostoevsky, Gogol, Goncharov, and Tolstoy."
        "</p>",
        unsafe_allow_html=True,
    )

    if not st.session_state["corpus_ready"]:
        try:
            st.session_state["corpus"] = _prepare_corpus_ui()
            st.session_state["corpus_ready"] = True
        except Exception as exc:  # noqa: BLE001 - surfacing setup issues to user is intentional.
            st.error(
                "Corpus setup failed. Please check your internet connection and verify source URLs "
                f"in data_loader.py.\n\nDetails: {exc}"
            )

    if st.session_state["corpus_ready"]:
        if st.button("Start Quiz", use_container_width=True, type="primary"):
            _start_new_quiz()
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def _render_quiz() -> None:
    """Render active quiz round with answer buttons and immediate feedback."""
    round_idx = st.session_state["current_round_idx"]
    rounds: List[QuizRound] = st.session_state["rounds"]
    current_round = rounds[round_idx]

    st.title("Readerquizz - Guess the Russian Author")
    st.markdown(f"<p class='rq-subtle'>Round {round_idx + 1} of {TOTAL_ROUNDS}</p>", unsafe_allow_html=True)
    st.progress(round_idx / TOTAL_ROUNDS)

    st.markdown("<div class='rq-card'>", unsafe_allow_html=True)
    st.markdown(f"<p class='rq-excerpt'>\"{current_round.excerpt}\"</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<p class='rq-subtle'>Who wrote this passage?</p>", unsafe_allow_html=True)

    columns = st.columns(2)
    for idx, option in enumerate(current_round.options):
        with columns[idx % 2]:
            if not st.session_state["answered"]:
                clicked = st.button(
                    option,
                    key=f"choice_{round_idx}_{option}",
                    use_container_width=True,
                )
                if clicked:
                    is_correct = check_answer(current_round, option)
                    st.session_state["answered"] = True
                    st.session_state["selected_author"] = option
                    st.session_state["last_answer_correct"] = is_correct
                    if is_correct:
                        st.session_state["score"] += 1
                    st.rerun()
            else:
                selected = st.session_state["selected_author"]
                correct_author = current_round.correct_author

                if option == selected and st.session_state["last_answer_correct"]:
                    css_class = "rq-option-state correct"
                elif option == selected and not st.session_state["last_answer_correct"]:
                    css_class = "rq-option-state wrong"
                elif option == correct_author:
                    css_class = "rq-option-state answer"
                else:
                    css_class = "rq-option-state"

                st.markdown(f"<div class='{css_class}'>{option}</div>", unsafe_allow_html=True)

    if st.session_state["answered"]:
        selected = st.session_state["selected_author"]
        correct_author = current_round.correct_author
        correct_book = current_round.book

        if st.session_state["last_answer_correct"]:
            st.success(f"Correct. Author: {correct_author} | Book: {correct_book}")
        else:
            st.error(
                f"Not quite. You selected {selected}, but the correct answer is "
                f"{correct_author} from {correct_book}."
            )

        completed = round_idx + 1
        st.markdown(
            f"<p class='rq-score'>Current score: {st.session_state['score']} / {completed}</p>",
            unsafe_allow_html=True,
        )

        next_label = "See Results" if completed >= TOTAL_ROUNDS else "Next Round"
        if st.button(next_label, use_container_width=True, type="primary"):
            _go_to_next_round_or_results()
            st.rerun()


def _render_results() -> None:
    """Render final score and restart controls."""
    score = st.session_state["score"]
    percent = int((score / TOTAL_ROUNDS) * 100)
    comment = score_comment(score, TOTAL_ROUNDS)

    st.title("Final Results")
    st.markdown("<div class='rq-card'>", unsafe_allow_html=True)
    st.markdown(f"<p class='rq-score'>You got {score}/{TOTAL_ROUNDS}</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='rq-subtle'>Accuracy: {percent}%</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='rq-subtle'>{comment}</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Restart Quiz", use_container_width=True, type="primary"):
        _start_new_quiz()
        st.rerun()

    if st.button("Back To Home", use_container_width=True):
        st.session_state["view"] = "home"
        st.rerun()


def main() -> None:
    """Application entrypoint."""
    _configure_page()
    _init_state()

    view = st.session_state["view"]
    if view == "home":
        _render_home()
    elif view == "quiz":
        _render_quiz()
    else:
        _render_results()


if __name__ == "__main__":
    main()