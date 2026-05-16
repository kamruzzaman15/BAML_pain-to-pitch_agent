"""
BAML Pain-to-Pitch Agent — main pipeline.

Run (recommended, generates BAML rewrites):
    python main.py

Smaller faster run but STILL generates rewrites:
    python main.py --queries 6 --max-per-query 5

The --skip-fix flag exists only for debugging. If you use it, Stage 7
will print a loud SKIPPED banner so you know the BAML rewrites are empty
on purpose. Do NOT use --skip-fix for your final results.

Pipeline stages:
    1 search  2 dedup  3 fetch  4 snippet  5 qualify
    6 enrich  7 BAML fix  8 outreach  9 rank + export
"""

import argparse
import sys

import config
from src import exporters
from src.fix_generator import generate_fix
from src.github_client import GitHubClient
from src.ollama_client import OllamaClient
from src.outreach_generator import generate_outreach
from src.qualifier import passes_threshold, qualify
from src.ranker import rank
from src.repo_enricher import enrich_lead
from src.search_queries import ALL_QUERIES
from src.snippet_extractor import extract_snippet


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BAML Pain-to-Pitch Agent")
    p.add_argument("--max-per-query", type=int, default=config.MAX_RESULTS_PER_QUERY)
    p.add_argument("--max-qualify", type=int, default=config.MAX_QUALIFY)
    p.add_argument("--queries", type=int, default=len(ALL_QUERIES),
                   help="use only the first N search queries")
    p.add_argument("--skip-fix", action="store_true",
                   help="DEBUG ONLY: skip BAML rewrite (leaves it empty)")
    p.add_argument("--skip-outreach", action="store_true",
                   help="DEBUG ONLY: skip outreach drafting")
    return p.parse_args()


def banner(text: str) -> None:
    print("\n" + "=" * 64)
    print(text)
    print("=" * 64)


def main() -> None:
    args = parse_args()
    config.validate()
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    gh = GitHubClient(config.GITHUB_TOKEN)
    llm = OllamaClient()

    if not llm.health_check():
        print(
            f"\n[error] Cannot reach Ollama at {config.OLLAMA_HOST}.\n"
            f"Start it with:  ollama serve\n"
            f"And pull the model:  ollama pull {config.OLLAMA_MODEL}\n"
        )
        sys.exit(1)

    print(f"Using Ollama model: {llm.model}")
    queries = ALL_QUERIES[: args.queries]

    # -----------------------------------------------------------------
    # Stage 1: search
    # -----------------------------------------------------------------
    banner("STAGE 1 — GitHub code search")
    raw: list[dict] = []
    for i, q in enumerate(queries, start=1):
        print(f"[{i}/{len(queries)}] query: {q}")
        results = gh.search_code(q, args.max_per_query)
        print(f"   -> {len(results)} results")
        raw.extend(results)
        if len(raw) >= config.MAX_RAW_CANDIDATES:
            print("   reached MAX_RAW_CANDIDATES, stopping search")
            break
        if i < len(queries):
            gh.pause_between_code_searches()

    raw = raw[: config.MAX_RAW_CANDIDATES]
    exporters.save_raw_candidates(raw)
    print(f"\nsaved {len(raw)} raw candidates -> {config.RAW_CANDIDATES_CSV}")
    if not raw:
        print(
            "\nNo search results at all. Your GITHUB_TOKEN is likely "
            "invalid or missing the public repo read scope."
        )
        return

    # -----------------------------------------------------------------
    # Stage 2: dedup
    # -----------------------------------------------------------------
    banner("STAGE 2 — deduplicate")
    seen = set()
    deduped: list[dict] = []
    for r in raw:
        key = f"{r['repo_full_name']}::{r['file_path']}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    print(f"{len(raw)} -> {len(deduped)} unique candidate files")

    # -----------------------------------------------------------------
    # Stages 3 & 4: fetch + extract snippet
    # -----------------------------------------------------------------
    banner("STAGE 3 & 4 — fetch files and extract snippets")
    with_snippets: list[dict] = []
    for i, lead in enumerate(deduped[: args.max_qualify], start=1):
        print(f"[{i}] {lead['repo_full_name']} :: {lead['file_path']}")
        content = gh.get_file_content(lead["repo_full_name"], lead["file_path"])
        if not content:
            print("   [skip] could not fetch file")
            continue
        snip = extract_snippet(content)
        if not snip:
            print("   [skip] no anchor found in file")
            continue
        lead.update(snip)
        with_snippets.append(lead)
    print(f"\n{len(with_snippets)} candidates have usable snippets")

    # -----------------------------------------------------------------
    # Stage 5: qualify
    # -----------------------------------------------------------------
    banner("STAGE 5 — qualify pain with local model")
    qualified: list[dict] = []
    guard_drops = 0
    for i, lead in enumerate(with_snippets, start=1):
        print(f"[{i}/{len(with_snippets)}] {lead['repo_full_name']}")
        qual = qualify(lead, llm)
        if qual is None:
            print("   [skip] model returned no valid JSON")
            continue
        lead.update(qual)
        if qual.get("rejected_by_guard"):
            guard_drops += 1
            print("   guard: no LLM call in snippet -> drop (false positive)")
            continue
        keep = passes_threshold(qual)
        print(
            f"   relevant={qual.get('is_baml_relevant')} "
            f"pain={qual.get('pain_score')} "
            f"conf={qual.get('confidence')} -> "
            f"{'KEEP' if keep else 'drop'}"
        )
        if keep:
            qualified.append(lead)

    exporters.save_qualified(qualified)
    print(
        f"\n{guard_drops} dropped by the no-LLM guard (false positives "
        f"removed)\n{len(qualified)} qualified leads -> "
        f"{config.QUALIFIED_LEADS_CSV}"
    )

    if not qualified:
        print(
            "\nNo leads passed. Either the search found weak matches, or "
            "the threshold is strict. Lower MIN_PAIN_SCORE or "
            "MIN_CONFIDENCE in config.py and run again."
        )
        return

    # -----------------------------------------------------------------
    # Stage 6: enrich
    # -----------------------------------------------------------------
    banner("STAGE 6 — enrich with repo metadata")
    for i, lead in enumerate(qualified, start=1):
        print(f"[{i}/{len(qualified)}] {lead['repo_full_name']}")
        enrich_lead(lead, gh)

    # -----------------------------------------------------------------
    # Stage 7: BAML-style fix  (banner ALWAYS prints)
    # -----------------------------------------------------------------
    if args.skip_fix:
        banner("STAGE 7 — SKIPPED  (--skip-fix flag was passed)")
        print(
            "BAML rewrites will be EMPTY in the output because you ran "
            "with --skip-fix.\nRemove that flag and run again to generate "
            "the BAML rewrites for your submission."
        )
    else:
        banner("STAGE 7 — generate illustrative BAML-style fix")
        fix_ok = 0
        for i, lead in enumerate(qualified, start=1):
            print(f"[{i}/{len(qualified)}] {lead['repo_full_name']}")
            fix = generate_fix(lead, llm)
            if fix and str(fix.get("baml_schema_or_function", "")).strip():
                lead.update(fix)
                fix_ok += 1
                print("   fix generated OK")
            else:
                print("   [warn] fix generation failed after retries")
        print(f"\nBAML rewrites generated: {fix_ok}/{len(qualified)}")
        if fix_ok == 0:
            print(
                "All fixes failed. Check that the model is pulled and "
                "responding. Try a different OLLAMA_MODEL in .env, for "
                "example qwen2.5-coder:7b or llama3.1:8b."
            )

    # -----------------------------------------------------------------
    # Stage 8: outreach  (banner ALWAYS prints)
    # -----------------------------------------------------------------
    if args.skip_outreach:
        banner("STAGE 8 — SKIPPED  (--skip-outreach flag was passed)")
    else:
        banner("STAGE 8 — draft outreach messages")
        msg_ok = 0
        for i, lead in enumerate(qualified, start=1):
            print(f"[{i}/{len(qualified)}] {lead['repo_full_name']}")
            msg = generate_outreach(lead, llm)
            if msg and str(msg.get("message", "")).strip():
                lead["outreach_message"] = msg.get("message", "")
                lead["tone_check"] = msg.get("tone_check", "")
                msg_ok += 1
            else:
                print("   [warn] outreach generation failed after retries")
        print(f"\nOutreach drafts generated: {msg_ok}/{len(qualified)}")

    # -----------------------------------------------------------------
    # Stage 9: rank + export
    # -----------------------------------------------------------------
    banner("STAGE 9 — rank and export")
    ranked = rank(qualified)
    exporters.save_final(ranked)
    exporters.write_top_examples(ranked)

    print(f"final ranked leads -> {config.FINAL_RANKED_CSV}")
    print(f"top examples       -> {config.TOP_EXAMPLES_MD}")

    print("\nTop leads:")
    for lead in ranked[: config.TOP_EXAMPLES_COUNT]:
        has_fix = "yes" if str(lead.get("baml_schema_or_function", "")).strip() else "NO"
        print(
            f"  #{lead['lead_rank']:<2} score={lead['lead_score']:<6} "
            f"pain={lead['pain_score']} fix={has_fix} "
            f"{lead['repo_full_name']}"
        )
    print("\nDone.")


if __name__ == "__main__":
    main()
