"""Re-apply enrichment passes (cluster, transit, scam, tips) to the existing
data/jobs.js in the Hub repo. No Firecrawl scrapes used.

Useful for deploying rule changes without paying for fresh data.

Writes to the Hub repo's data/jobs.js but does NOT push — you push via
GitHub Desktop after running this.

Usage:
    python reenrich.py
"""
from __future__ import annotations
import json
import logging
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "config"
sys.path.insert(0, str(PROJECT_ROOT))

from src import normalize
from src.enrich import scam as scam_mod
from src.enrich import classify, transit, ai
from src.output import write as write_output

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("reenrich")

load_dotenv(PROJECT_ROOT / ".env")
HUB_REPO_PATH = os.getenv("HUB_REPO_PATH", "").strip()
if not HUB_REPO_PATH:
    log.error("HUB_REPO_PATH not set in .env")
    sys.exit(1)

source = Path(HUB_REPO_PATH) / "data" / "jobs.js"
if not source.exists():
    log.error("No file at %s — nothing to re-enrich", source)
    sys.exit(1)

# Load existing jobs.js
content = source.read_text(encoding="utf-8")
match = re.search(r"window\.HUB_JOBS\s*=\s*(\[[\s\S]*?\]);\s*$", content, re.M)
if not match:
    log.error("Could not find HUB_JOBS array in %s", source)
    sys.exit(1)

jobs = json.loads(match.group(1))
log.info("Loaded %d jobs from %s", len(jobs), source)

# Reset enrichment fields so they get recomputed cleanly
for j in jobs:
    for k in ("category", "edu_level", "edu_label",
              "transit_accessible", "transit_agency", "transit_agency_url",
              "tip_resume", "tip_cover"):
        j.pop(k, None)

# Re-apply scam filter (in case rules changed)
kept = []
dropped = 0
for j in jobs:
    is_scam, reason = scam_mod.is_scam(j)
    if is_scam and not j.get("submitted"):
        log.info("Scam-filtered: %s @ %s (%s)", j.get("title"), j.get("employer"), reason)
        dropped += 1
        continue
    kept.append(j)
log.info("After scam filter: %d (dropped %d)", len(kept), dropped)

# Re-apply enrichment passes
cluster_rules = classify.load_cluster_rules(CONFIG_DIR)
transit_agencies = transit.load_agencies(CONFIG_DIR)
for j in kept:
    classify.enrich(j, cluster_rules)
    transit.enrich(j, transit_agencies)
ai.enrich_all(kept, config_dir=CONFIG_DIR)

# Rebuild the prefilled "Send to client" email
for j in kept:
    title = j.get("title", "")
    employer = j.get("employer", "")
    location = j.get("location", "")
    salary = j.get("salary", "Not listed")
    url = j.get("url", "")
    company_url = j.get("company_url") or (
        "https://duckduckgo.com/?q=%21ducky+" + quote_plus(f"{employer} about us")
    )
    tip_r = j.get("tip_resume", "")
    tip_c = j.get("tip_cover", "")
    j["client_subject"] = f"Job opportunity: {title} at {employer}"
    j["client_body"] = (
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

# Write back to Hub repo (no push)
out = write_output(kept, hub_repo_path=HUB_REPO_PATH, dry_run=False, do_git_push=False)
log.info("Wrote %d re-enriched jobs to %s", len(kept), out)
log.info("No Firecrawl credits used. Push via GitHub Desktop to deploy.")
