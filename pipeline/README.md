# Weekly Job Report Pipeline

Scrapes job listings from four sources, enriches them with AI-generated tips and transit info, and writes `data/jobs.js` into the Hub website repo.

**Runs:** weekly on Kevin's work PC via Windows Task Scheduler.
**Output:** `C:\Users\KevinWestwood\Documents\GitHub\data\jobs.js` (the Hub site) — then auto-commits and pushes.

## Sources

1. **Job Bank Canada** — public JSON-ish endpoint, no Firecrawl needed
2. **Workforce Planning Boards** — Firecrawl scrape
3. **Employer career pages** — Firecrawl scrape, list in `config/employers.csv`
4. **MS Form counsellor submissions** — Excel file at `C:\Users\KevinWestwood\OneDrive - PATH Employment Services\Submit a job for the Weekly Jobs Listings.xlsx`

## Regions

Hamilton, Niagara, Brantford, Haldimand-Norfolk, Halton.

## Project layout

```
weekly-job-report-pipeline/
├── config/
│   ├── employers.csv              # 54 employers, careers URLs
│   ├── wpb_sources.yaml           # Workforce Planning Board URLs
│   ├── transit_agencies.yaml      # transit agency mapping per region
│   └── cluster_rules.yaml         # keyword rules for occupation cluster
├── src/
│   ├── sources/
│   │   ├── jobbank.py
│   │   ├── wpb.py
│   │   ├── employers.py
│   │   └── msform.py
│   ├── enrich/
│   │   ├── scam.py
│   │   ├── classify.py            # cluster + education
│   │   ├── transit.py
│   │   └── ai.py                  # Anthropic API for resume/cover tips
│   ├── normalize.py               # common job schema
│   ├── output.py                  # writes data/jobs.js + git push
│   └── main.py                    # orchestrator
├── data/
│   └── gtfs_cache/                # transit data cache (gitignored)
├── .env                           # API keys (gitignored)
├── .env.example                   # template
├── .gitignore
├── requirements.txt
└── run.bat                        # Task Scheduler entry point
```

## Setup (work PC, ~10 minutes)

1. Copy this folder into a non-OneDrive location: `C:\Users\KevinWestwood\Documents\weekly-job-report-pipeline\` (or whatever clean path you want).
2. Open Command Prompt in that folder.
3. `python -m venv .venv`
4. `.venv\Scripts\activate`
5. `pip install -r requirements.txt`
6. Copy `.env.example` to `.env` and paste in your API keys.
7. Test it: `python -m src.main --dry-run`
8. When ready to deploy: `python -m src.main`
9. Add to Windows Task Scheduler — run `run.bat` weekly.

## Modes

- `--dry-run` — runs all scrapers, writes output to `data/jobs-test.js` in this folder. Does NOT touch the Hub repo. **Default for safety.**
- (no flag, or `--prod`) — writes to the Hub repo's `data/jobs.js` and commits + pushes.
