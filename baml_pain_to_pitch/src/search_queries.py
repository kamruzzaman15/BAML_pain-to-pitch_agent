"""
GitHub code-search query patterns.

These are intentionally simple keyword queries because the GitHub REST
code-search endpoint uses legacy search behavior and does not support
complex boolean syntax well.

Keep the list short for a clean prototype. 6 Python + 4 TypeScript is
enough to demonstrate the agent.
"""

PYTHON_QUERIES = [
    '"json.loads" "openai" language:Python',
    '"JSONDecodeError" "openai" language:Python',
    '"json.loads" "chat.completions" language:Python',
    '"retry" "json.loads" "openai" language:Python',
    '"re.search" "openai" "json" language:Python',
    '"response_format" "json.loads" language:Python',
]

TYPESCRIPT_QUERIES = [
    '"JSON.parse" "openai" language:TypeScript',
    '"try" "JSON.parse" "openai" language:TypeScript',
    '"JSON.parse" "chat.completions" language:TypeScript',
    '"retry" "JSON.parse" "LLM" language:TypeScript',
]

ALL_QUERIES = PYTHON_QUERIES + TYPESCRIPT_QUERIES
