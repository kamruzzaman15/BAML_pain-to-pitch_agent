# BAML Pain-to-Pitch Agent

A lightweight GTM agent for **BAML** (by Boundary). It finds developers who
already have the exact pain BAML solves, then drafts a code-specific outreach
message for them.

> Built for the Basis Set Ventures AI Fellow project, Track 2 (Agentic GTM).
> Chosen company: BAML, which was my number one ranked company in the
> prioritization task.

---

## The idea in one line

Many developers have BAML's pain but never search for "BAML". They reveal it
in their public code through manual `json.loads`, regex cleanup, and retry
loops around model calls. This agent finds that pain in public GitHub code,
qualifies it, and produces a personalized outreach draft with an illustrative
BAML rewrite.

Nothing is auto-sent. A human reviews every draft.

---

## Why this is a real GTM mechanism, not a generic outbound bot

- It targets **high-intent technical signals**, not vague demographics.
- Each message points at the developer's **own code** and shows a concrete fix.
- It is a **repeatable pipeline**, so it scales beyond manual sourcing.
- It uses a **deterministic precision guard**, so it does not spam false leads.

---

## How it works

The pipeline has 9 stages. Each stage prints a banner at run time so you can
see exactly what is happening.

| Stage | Name      | What happens |
|------:|-----------|--------------|
| 1 | Search    | GitHub code search with structured-output pain patterns |
| 2 | Dedup     | Remove duplicate repo and file hits |
| 3 | Fetch     | Download the candidate file content |
| 4 | Snippet   | Extract a small code window around the painful line |
| 5 | Qualify   | A no-LLM guard drops false positives, then the model scores the rest |
| 6 | Enrich    | Add repo metadata: stars, activity, owner type |
| 7 | BAML fix  | Generate an illustrative BAML rewrite, with a quality gate |
| 8 | Outreach  | Draft a short, non-salesy message for human review |
| 9 | Rank      | Score and sort leads, then export |

Ranking score (transparent and tunable in `config.py`):

```
lead_score = 0.50*pain + 0.25*confidence + 0.15*repo_activity + 0.10*org_fit
```

---

## Stack

- **GitHub REST API** for code search and file content
- **Ollama** local model API (no paid LLM API used)
- Model used: `qwen2.5-coder:7b`
- Python, pandas

---

## Setup

```bash
git clone <your-repo-url>
cd baml_pain_to_pitch

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# open .env and set GITHUB_TOKEN to your GitHub personal access token
```

A free GitHub personal access token with public repo read scope is enough:
https://github.com/settings/tokens

Install and start Ollama, then pull the model:

```bash
# install: https://ollama.com/download
ollama serve
ollama pull qwen2.5-coder:7b
```

The only file you must edit is `.env` (just the `GITHUB_TOKEN` line).

---

## Run

```bash
python main.py
```

Smaller, faster run:

```bash
python main.py --queries 6 --max-per-query 5
```

Do not pass `--skip-fix` for real results. That flag is debug only and leaves
the BAML rewrites empty on purpose.

---

## Outputs

All written to `outputs/`:

| File | Contents |
|------|----------|
| `raw_candidates.csv` | every code-search hit before dedup |
| `qualified_leads.csv` | leads that passed the pain threshold |
| `final_ranked_leads.csv` | full ranked table with all fields |
| `top_examples.md` | best examples formatted for review |

---

## Example result

The strongest real lead the agent produced was **`cursor/eval`**, an LLM eval
harness from Cursor. It found a manual async retry loop around an OpenAI call:

```python
async def retry(sem, fn):
    for i in range(1, 3):
        try:
            async with sem:
                return await fn()
        except Exception as e:
            print(e); print('retrying')
            time.sleep(0.3*i)
    return await fn()
```

The agent diagnosed the pain, produced an illustrative BAML rewrite, and
drafted a short outreach message that points at this exact pattern. See
`outputs/top_examples.md` for the full example.

---

## Honest limitations

- The BAML rewrite runs on a small local model, so it sometimes copies the
  reference schema instead of inferring fields from the real code. The
  rewrites are directionally correct but not always domain-accurate.
- GitHub code search is rate limited and has noisy metadata.
- The no-LLM guard is a heuristic. It favors precision over recall on
  purpose. It is better to show a few real leads than many noisy ones.

## What I would improve with more time

- Use a stronger model for the rewrite step only.
- Force schema fields to be inferred strictly from the snippet.
- Add GitHub issue and discussion mining, not only code search.
- Deduplicate by company.
- Add a feedback loop where human review updates the ranking rubric.

---

## How it was built

I prototyped the agent with Codex, then manually checked the output at each
step and adjusted it where needed. The build was iterative. Early runs
surfaced false positives and weak rewrites, which I fixed with a precision
guard and a BAML quality gate. The full debugging history is in the project
write-up.

## Repo layout

```
baml_pain_to_pitch/
├── main.py              # pipeline orchestrator
├── config.py            # all tunable settings
├── src/                 # one module per stage
├── prompts/             # qualify / fix / outreach prompts
├── schemas/             # JSON schemas for structured model output
└── outputs/             # generated results
```
