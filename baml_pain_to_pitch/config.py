"""
Central configuration for the BAML Pain-to-Pitch Agent.

All tunable numbers live here so you do not need to dig into the modules.
Values are read from the .env file when present, otherwise sane defaults
are used.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------
# Credentials and endpoints
# ---------------------------------------------------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip().rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b").strip()

GITHUB_API = "https://api.github.com"

# ---------------------------------------------------------------------
# Scale limits (keep small for a clean prototype)
# ---------------------------------------------------------------------
MAX_RESULTS_PER_QUERY = 5      # top N code search results per query
MAX_RAW_CANDIDATES = 50        # hard cap on candidate files before dedup
MAX_QUALIFY = 40               # cap how many snippets we send to the model

# ---------------------------------------------------------------------
# GitHub rate-limit safety
# Code search is limited to ~10 requests / minute, so we pause between
# code-search calls. 7 seconds keeps us safely under the limit.
# ---------------------------------------------------------------------
CODE_SEARCH_SLEEP_SECONDS = 7
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

# ---------------------------------------------------------------------
# Snippet extraction window
# ---------------------------------------------------------------------
SNIPPET_LINES_BEFORE = 15
SNIPPET_LINES_AFTER = 25

# Anchors used to locate the painful line inside a file
SNIPPET_ANCHORS = [
    "json.loads",
    "JSON.parse",
    "JSONDecodeError",
    "re.search",
    "re.findall",
    "retry",
]

# ---------------------------------------------------------------------
# Qualification acceptance thresholds
# ---------------------------------------------------------------------
MIN_PAIN_SCORE = 4         # keep only pain_score >= this
MIN_CONFIDENCE = 0.70      # keep only confidence >= this

# ---------------------------------------------------------------------
# Ranking weights (must sum to 1.0)
# ---------------------------------------------------------------------
WEIGHT_PAIN = 0.50
WEIGHT_CONFIDENCE = 0.25
WEIGHT_ACTIVITY = 0.15
WEIGHT_ORG_FIT = 0.10

# Repo is considered "active" if pushed within this many days
ACTIVE_DAYS = 90

# ---------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------
OUTPUT_DIR = PROJECT_ROOT / "outputs"
RAW_CANDIDATES_CSV = OUTPUT_DIR / "raw_candidates.csv"
QUALIFIED_LEADS_CSV = OUTPUT_DIR / "qualified_leads.csv"
FINAL_RANKED_CSV = OUTPUT_DIR / "final_ranked_leads.csv"
TOP_EXAMPLES_MD = OUTPUT_DIR / "top_examples.md"

# How many polished examples to write into top_examples.md
TOP_EXAMPLES_COUNT = 3

PROMPTS_DIR = PROJECT_ROOT / "prompts"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"


def validate() -> None:
    """Fail early with a clear message if the token is missing."""
    if not GITHUB_TOKEN or GITHUB_TOKEN == "your_github_personal_access_token_here":
        raise SystemExit(
            "\nGITHUB_TOKEN is not set.\n"
            "Open the file '.env' and set GITHUB_TOKEN to your GitHub "
            "personal access token, then run again.\n"
        )
