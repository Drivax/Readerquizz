# Readerquizz



Readerquizz is a  Streamlit web app : https://readerquizz.streamlit.app/ where players read a short literary extract and guess which Russian author wrote it.

Each quiz contains exactly 10 rounds. In every round, the app shows one extract made of exactly 2 sentences and 4 author options:

- Dostoevsky
- Gogol
- Goncharov
- Tolstoy

At the end, the app displays the final score out of 10, percentage, and an encouraging literary-style summary.

## Project Description

Readerquizz is designed as a lightweight educational game that blends literary discovery with pattern recognition.

On first launch, the app:

1. Downloads public domain texts for each target author.
2. Stores raw text files in a local `data/raw/` directory.
3. Cleans and preprocesses the corpus.
4. Extracts many 2-sentence passages and saves a processed dataset in `data/processed/`.

On later launches, Readerquizz reuses local files and does not re-download data unless those files are missing.

## Features

- Streamlit-based interactive quiz interface.
- Automatic first-run corpus download with progress indication.
- Local caching of raw and processed data in `data/`.
- Exactly 10 rounds per game.
- Exactly 2 sentences per round extract.
- 4 shuffled answer options each round.
- Immediate feedback after each answer.
- Progress tracking (for example: round 3 of 10).
- Final results screen with score, percentage, and dynamic encouragement.
- One-click quiz restart.
- Clean, literary-inspired dark-friendly UI styling.

## File Structure

```text
Readerquizz/
	app.py
	data_loader.py
	quiz_engine.py
	requirements.txt
	README.md
	data/
		raw/
		processed/
```

## How To Run The App

1. Clone or download this repository.
2. Create and activate a Python environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Launch Streamlit:

```bash
streamlit run app.py
```

5. Open the local URL shown in the terminal (usually `http://localhost:8501`).

## Data Sources

Readerquizz uses public domain text sources from Project Gutenberg (and compatible Gutenberg mirror endpoints where needed).

Configured corpus targets include:

- Fyodor Dostoevsky (for example: *Crime and Punishment* and other Gutenberg texts)
- Nikolai Gogol (for example: *Dead Souls*)
- Ivan Goncharov (for example: Gutenberg-hosted editions/translations)
- Leo Tolstoy (for example: *Anna Karenina*, *War and Peace*)

Exact URLs are defined in `data_loader.py` and can be adjusted easily if a source changes.

## Notes

- First launch may take a while depending on network speed.
- If a source URL becomes unavailable, replace it in `data_loader.py` with another public domain source.
- Processed quiz extracts are saved locally to avoid repeated heavy preprocessing.
