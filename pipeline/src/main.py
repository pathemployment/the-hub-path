"""Pipeline orchestrator.

Usage:
  python -m src.main --dry-run     # write to data/jobs-test.js, no push
  python -m src.main                # same as --dry-run (default for safety)
  python -m src.main --prod         # write to Hub repo's data/jobs.js
  python -m src.main --prod --push  # additionally git commit + push
"""
from __future__ import annotations
import argparse
import logging
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

from src import normalize
from src.enrich import scam as scam_mod
from src.enrich import classify, transit, ai
from src.output import write as write_output
from src.sources import jobbank, msform, employers, wpb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pipeline")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


def _try_firecrawl():
    api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not api_key or api_key.startswith("fc-your-key"):
        log.warning("FIRECRAWL_API_KEY not set — Firecrawl-based sources will be skipped")
        return None
    try:
        from firecrawl import Firecrawl
        return Firecrawl(api_key=api_key)
    except Exception as e:
        log.warning("Firecrawl client init failed: %s", e)
        return None


def _build_client_email(job: dict) -> None:
    """Add client_subject + client_body fields used by the 'Send to client' button."""
    title = job.get("title", "")
    employer = job.get("employer", "")
    location = job.get("location", "")
    salary = job.get("salary", "Not listed")
    url = job.get("url", "")
    company_url = job.get("company_url") or (
        "https://duckduckgo.com/?q=%21ducky+" + quote_plus(f"{employer} about us")
    )
    tip_r = job.get("tip_resume", "")
    tip_c = job.get("tip_cover", "")

    job["client_subject"] = f"Job opportunity: {title} at {employer}"
    job["client_body"] = (
        "Hi [client name],\n\n"
        "I came across this job and thought it might be a good fit. Take a look:\n\n"
        "THE JOB\n"
        f"{title}\n"
        f"{employer} — {location}" + (f"  {salary}" if salary and salary != "Not listed" else "") + "\n\n"
        "APPLY HERE\n"
        f"{url}\n\n"
        "ABOUT THE EMPLOYER\n"
        f"{company_url}\n\n"
        + (f"RESUME TIPS\n{tip_r}\n\n" if tip_r else "")
        + (f"COVER LETTER ANGLE\n{tip_c}\n\n" if tip_c else "")
        + "Want to apply, or talk through whether it is a fit? Let me know.\n\n—\n"
    )


def run(args) -> int:
    load_dotenv(PROJECT_ROOT / ".env")

    firecrawl_client = _try_firecrawl()
    cluster_rules = classify.load_cluster_rules(CONFIG_DIR)
    transit_agencies = transit.load_agencies(CONFIG_DIR)

    all_jobs: list[dict] = []

    # ---- Source 1: Job Bank ----
    if firecrawl_client and not args.skip_jobbank:
        log.info("Source: Job Bank")
        all_jobs.extend(jobbank.fetch(firecrawl_client))

    # ---- Source 2: Workforce Planning Boards (DISABLED) ----
    # WPB sites don't actually host job listings; they link out to other
    # job boards. After verification, no useful jobs ever came through.
    # Keeping the module for future use if a WPB adds a real listings page.
    # Re-enable by removing 'or True' below.
    if firecrawl_client and not args.skip_wpb and not True:
        log.info("Source: Workforce Planning Boards")
        all_jobs.extend(wpb.fetch(firecrawl_client, config_dir=CONFIG_DIR))

    # ---- Source 3: Employer career pages (bi-weekly cache) ----
    if not args.skip_employers:
        log.info("Source: Employer career pages")
        all_jobs.extend(employers.fetch(
            firecrawl_client,
            config_dir=CONFIG_DIR,
            project_root=PROJECT_ROOT,
            force_refresh=args.refresh_employers,
        ))

    # ---- Source 4: MS Form submitted ----
    if not args.skip_msform:
        log.info("Source: MS Form Excel")
        all_jobs.extend(msform.fetch(firecrawl_client=firecrawl_client, project_root=PROJECT_ROOT))

    log.info("Total raw jobs: %d", len(all_jobs))

    # ---- Filter to known regions ----
    # Submitted (counsellor-vetted) jobs are kept regardless of region —
    # counsellors meant for these to appear, even if location extraction failed.
    in_region = [j for j in all_jobs
                 if j.get("region") in normalize.REGIONS or j.get("submitted")]
    log.info("In-region or submitted: %d (dropped %d)", len(in_region), len(all_jobs) - len(in_region))

    # ---- Dedupe ----
    deduped = normalize.dedupe(in_region)
    log.info("After dedupe: %d", len(deduped))

    # ---- Filter recent (14 days) ----
    recent = normalize.filter_recent(deduped, window_days=args.window_days)
    log.info("Within %d-day window: %d", args.window_days, len(recent))

    # ---- Scam filter ----
    kept = []
    dropped = 0
    for j in recent:
        is_scam, reason = scam_mod.is_scam(j)
        if is_scam and not j.get("submitted"):  # never drop counsellor-vetted
            log.info("Scam-filtered: %s @ %s (%s)", j.get("title"), j.get("employer"), reason)
            dropped += 1
            continue
        kept.append(j)
    log.info("After scam filter: %d (dropped %d)", len(kept), dropped)

    # ---- Classify + transit enrichment ----
    for j in kept:
        classify.enrich(j, cluster_rules)
        transit.enrich(j, transit_agencies)

    # ---- Tip enrichment (template-based, no API cost) ----
    if not args.skip_ai:
        ai.enrich_all(kept, config_dir=CONFIG_DIR)

    # ---- Client email pre-build ----
    for j in kept:
        _build_client_email(j)

    # ---- Output ----
    out_path = write_output(
        kept,
        hub_repo_path=os.getenv("HUB_REPO_PATH", "").strip() or None,
        dry_run=not args.prod,
        window_days=args.window_days,
        do_git_push=args.push,
    )
    log.info("Done. %d jobs -> %s", len(kept), out_path)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Weekly job report pipeline")
    parser.add_argument("--prod", action="store_true", help="Write to Hub repo (default: dry-run to local test file)")
    parser.add_argument("--push", action="store_true", help="git commit + push after writing (requires --prod)")
    parser.add_argument("--window-days", type=int, default=14)
    parser.add_argument("--skip-jobbank", action="store_true")
    parser.add_argument("--skip-wpb", action="store_true")
    parser.add_argument("--skip-employers", action="store_true")
    parser.add_argument("--skip-msform", action="store_true")
    parser.add_argument("--skip-ai", action="store_true", help="skip tip enrichment (uncommon)")
    parser.add_argument("--refresh-employers", action="store_true",
                        help="force a fresh employer scrape (overrides 13-day cache)")
    parser.add_argument("--dry-run", action="store_true", help="(default) write to local test file")
    args = parser.parse_args()

    sys.exit(run(args))


if __name__ == "__main__":
    main()
