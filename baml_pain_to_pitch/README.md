# BAML Pain-to-Pitch Agent

A lightweight GTM agent for **BAML** (Track 2, Agentic GTM).

It finds public GitHub code that shows structured-output reliability pain
(manual `json.loads`, regex cleanup, retry loops around LLM output),
qualifies the pain with a local code model through Ollama, generates an
illustrative BAML-style rewrite, and drafts a short human-reviewed
outreach message. The final output is a ranked lead table plus a polished
examples report.

Nothing is ever auto-sent. A human reviews every draft.

---

## 1. The only file you must edit

Copy the env template and add your GitHub token:

```bash
cp .env.example .env
```

Then open **`.env`** and set:

```
GITHUB_TOKEN=ghp_your_real_token_here
```

That is the **only required change**. A free GitHub personal access
token with public repo read scope is enough:
https://github.com/settings/tokens

Optionally in the same `.env` you can change `OLLAMA_MODEL` if you want a
lighter model (see below).

---

## 2. Setup

```bash
cd baml_pain_to_pitch
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Install and start Ollama, then pull the model:

```bash
# install: https://ollama.com/download
ollama serve                       # if not already running
ollama pull qwen3-coder-next       # primary recommendation
```

If `qwen3-coder-next` is too heavy for your machine, set a lighter model
in `.env`, for example:

```
OLLAMA_MODEL=qwen2.5-coder:7b
```

and `ollama pull qwen2.5-coder:7b`.

---

## 3. Run

```bash
python main.py
```

Helpful flags:

```bash
python main.py --queries 4 --max-per-query 5   # smaller, faster run
python main.py --max-qualify 20                 # cap model calls
python main.py --skip-fix                       # skip BAML rewrite
python main.py --skip-outreach                  # skip message drafting
```

---

## 4. Outputs

All written to `outputs/`:

| File                     | Contents                                  |
| ------------------------ | ----------------------------------------- |
| `raw_candidates.csv`     | every code-search hit before dedup        |
| `qualified_leads.csv`    | leads that passed the pain threshold      |
| `final_ranked_leads.csv` | full ranked table with all fields         |
| `top_examples.md`        | best 3 examples formatted for the write-up|

---

## 5. Tuning

Everything tunable is in **`config.py`**:

- `MIN_PAIN_SCORE`, `MIN_CONFIDENCE` — how strict qualification is
- `WEIGHT_*` — ranking weights
- `MAX_RESULTS_PER_QUERY`, `MAX_RAW_CANDIDATES`, `MAX_QUALIFY` — scale
- `CODE_SEARCH_SLEEP_SECONDS` — GitHub code-search rate-limit pause

If no leads pass, lower `MIN_PAIN_SCORE` to 3 or `MIN_CONFIDENCE` to 0.6.

---

## 6. Pipeline

```
1 search  ->  2 dedup  ->  3 fetch  ->  4 snippet  ->  5 qualify
   ->  6 enrich  ->  7 BAML fix  ->  8 outreach  ->  9 rank + export
```

## 7. Known limits

- GitHub code search has false positives (`json.loads` not from an LLM).
  The qualifier model filters these, but it is not perfect.
- Local model rewrites are illustrative sketches, not drop-in migrations.
- Public repo metadata does not always identify the real buyer.
- GitHub code search is rate limited (~10 req/min); the client pauses
  between searches automatically.
