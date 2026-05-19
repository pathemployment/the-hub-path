"""Employer career-page scraper.

Loads config/employers.csv, scrapes each careers URL via Firecrawl, and asks
Firecrawl's extraction layer to pull structured job listings.

To save Firecrawl credits, employer scrapes are cached for 13 days. The
weekly pipeline reuses the cache on off-weeks; the off-week run still
includes employer jobs (from cache), it just doesn't re-scrape them.

Each employer row in employers.csv:
  employer, careers_url, regions, typical_clusters, confidence, notes
"""
from __future__ import annotations
import csv
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from src.normalize import make_job

log = logging.getLogger(__name__)

CACHE_FRESH_DAYS = 13  # re-scrape every 14 days; 13 leaves a 1-day buffer


def load_employer_list(config_dir: Path | str) -> list[dict]:
    path = Path(config_dir) / "employers.csv"
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def _cache_path(project_root: Path) -> Path:
    return project_root / "data" / "employer_cache.json"


def _cache_is_fresh(cache_file: Path) -> bool:
    if not cache_file.exists():
        return False
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        ts = data.get("generated_at")
        if not ts:
            return False
        generated = datetime.fromisoformat(ts)
        return (datetime.now() - generated) < timedelta(days=CACHE_FRESH_DAYS)
    except Exception as e:
        log.warning("Cache read failed: %s", e)
        return False


def _load_cached_jobs(cache_file: Path) -> list[dict]:
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    return data.get("jobs", [])


def _write_cache(cache_file: Path, jobs: list[dict]) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(),
        "jobs": jobs,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch(firecrawl_client, employer_rows: list[dict] | None = None,
          config_dir: Path | str | None = None,
          project_root: Path | str | None = None,
          force_refresh: bool = False) -> list[dict]:
    """Scrape each employer's careers page. Returns list of normalized jobs.

    Uses a 13-day cache to keep Firecrawl usage under free-tier limits.
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent
    project_root = Path(project_root)
    cache_file = _cache_path(project_root)

    if not force_refresh and _cache_is_fresh(cache_file):
        cached = _load_cached_jobs(cache_file)
        log.info("Employer cache is fresh (<%d days). Using %d cached jobs.",
                 CACHE_FRESH_DAYS, len(cached))
        return cached

    if not firecrawl_client:
        log.warning("Firecrawl client not provided AND cache stale — skipping Employer source")
        return []
    if employer_rows is None and config_dir is not None:
        employer_rows = load_employer_list(config_dir)
    employer_rows = employer_rows or []

    jobs: list[dict] = []
    for row in employer_rows:
        name = (row.get("employer") or "").strip()
        url = (row.get("careers_url") or "").strip()
        regions = (row.get("regions") or "").strip()
        if not name or not url:
            continue

        log.info("Employer scrape: %s", name)
        company_url = _company_root(url)
        try:
            scraped = firecrawl_client.scrape(
                url,
                formats=["markdown"],
                only_main_content=True,
            )
            extracted = _extract_jobs_from_markdown(scraped, name)
        except Exception as e:
            log.warning("  failed for %s: %s", name, e)
            continue

        # Apply this employer's region info if we can't infer per-job
        default_region = _first_region(regions)
        for j in extracted:
            j = make_job(
                title=j["title"],
                employer=name,
                location=j.get("location") or default_region or "",
                url=j["url"],
                source="Employer Website",
                description=j.get("description", ""),
                salary=j.get("salary", "Not listed"),
                region=default_region,
                company_url=company_url,
            )
            jobs.append(j)

    # Write fresh cache so next run within 13 days can reuse
    _write_cache(cache_file, jobs)
    log.info("Cached %d employer jobs to %s", len(jobs), cache_file)
    return jobs


def _company_root(careers_url: str) -> str:
    """Get the root domain URL (scheme + host) of the careers page."""
    try:
        u = urlparse(careers_url)
        if u.scheme and u.netloc:
            return f"{u.scheme}://{u.netloc}"
    except Exception:
        pass
    return careers_url


def _first_region(regions_field: str) -> str | None:
    """employers.csv puts multi-region chains as 'A|B|C'. Use first as default."""
    if not regions_field:
        return None
    parts = [p.strip() for p in regions_field.split("|") if p.strip()]
    return parts[0] if parts else None


def _extract_jobs_from_markdown(scrape_result, employer: str) -> list[dict]:
    """Heuristic: pull job-like links from the markdown content.

    Each employer's site is different. v1 looks for markdown links whose text
    looks like a job title (short, capitalized words) and URL contains a
    job-indicator path segment (jobs/, careers/, position/, opening/, etc.).

    v2 would use Firecrawl's structured-extraction endpoint with a Pydantic
    schema. That's higher quality but uses more credits per scrape.
    """
    import re

    md = getattr(scrape_result, "markdown", None) or ""
    if not md:
        return []

    # Match [Link text](https://url)
    link_re = re.compile(r"\[([^\]]{3,120})\]\((https?://[^\)]+)\)")

    seen_urls: set[str] = set()
    jobs: list[dict] = []
    for m in link_re.finditer(md):
        text = m.group(1).strip()
        href = m.group(2).strip()
        if href in seen_urls:
            continue
        if not _looks_like_job_url(href):
            continue
        if not _looks_like_job_title(text):
            continue
        seen_urls.add(href)
        jobs.append({"title": text, "url": href})
    return jobs


# Known applicant-tracking-system (ATS) domain patterns. Any URL hitting one
# of these is virtually always a real job posting.
_KNOWN_ATS_PATTERNS = [
    "myworkdayjobs.com", "myworkday.com", ".wd1.", ".wd2.", ".wd3.", ".wd4.", ".wd5.",
    "icims.com",
    "smartrecruiters.com",
    "greenhouse.io",
    "lever.co",
    "successfactors.com",
    "taleo.net",
    "applytojob.com", "appcast.io",
    "hr.cloud.sap",
    "bamboohr.com",
    "ultipro.com", "myultipro.com",
    "ashbyhq.com",
    "personiohr.com",
    "recruitee.com",
    "jobvite.com",
    "phenompeople.com",
    "applicantstack.com",
    "breezy.hr",
    "join.com",
    "applytoeducation.com",
    "workable.com",
    "rita-recruit",
    "njoyn.com",
    "njoynjobs.com",
    "talemetry.com",
    "jobillico.com",
    "indeed.com/viewjob", "indeed.ca/viewjob",
    "linkedin.com/jobs/view",
    "jobbank.gc.ca/jobsearch/jobposting/",
    "civicjobs.ca",
]


def _looks_like_job_url(url: str) -> bool:
    """Accept only URLs that look like real job postings.

    Two acceptance criteria (either passes):
      1. URL is on a known ATS domain
      2. URL path contains a numeric job ID (4+ digits)
    """
    u = url.lower()
    if any(p in u for p in _KNOWN_ATS_PATTERNS):
        return True
    # Numeric job ID in path: /12345, /-12345, /_12345, /job-12345, etc.
    if re.search(r"[/\-_=](\d{4,})(?:[/?&#]|$)", u):
        return True
    return False


# Generic/structural strings that aren't real job titles
_JUNK_TITLE_PHRASES = {
    "careers", "career", "all jobs", "all positions", "view all", "search jobs",
    "more", "next", "previous", "home", "about", "about us", "contact",
    "contact us", "sign in", "log in", "register", "apply now", "apply here",
    "find a job", "browse jobs", "join us", "join our team", "open positions",
    "high contrast", "accessibility", "skip to content", "skip to main content",
    "translate", "language", "menu",
}
_JUNK_TITLE_PREFIXES = (
    "careers at ", "jobs at ", "career at ",
    "search ", "view ", "browse ", "explore ",
    "welcome to ", "join ", "find ",
)


def _looks_like_job_title(text: str) -> bool:
    """Filter out navigation links, page titles, image alt text, etc."""
    t = text.strip()
    if len(t) < 4 or len(t) > 100:
        return False
    t_low = t.lower()
    if t_low in _JUNK_TITLE_PHRASES:
        return False
    if any(t_low.startswith(p) for p in _JUNK_TITLE_PREFIXES):
        return False
    # Image alt text often reads as a descriptive sentence
    if re.search(r"\b(smiling|posing|wearing|holding|standing|sitting|background|image|photo|picture|logo|icon)\b", t_low):
        return False
    # Should have at least one space (most job titles are 2+ words),
    # unless it's a single short specialized term (e.g., "Cashier", "Electrician")
    if " " not in t and len(t) < 6:
        return False
    return True
