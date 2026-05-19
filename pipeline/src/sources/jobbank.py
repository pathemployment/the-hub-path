"""Job Bank Canada source.

Job Bank's URL filters (fpr, fctr, locationstring, flocation) are all ignored
by their search page — they always return Canada-wide popular jobs. The ONLY
parameter that actually narrows results is `searchstring=`, which does a
text search across the listings. We use it as a pseudo-location filter by
searching for each region's primary city, then validate by inspecting each
job's actual location field (false-positives get dropped by infer_region).

Each job in the markdown looks roughly like:

    [**<noise prefix> <SourceLabel><title>**\\\\
    \\\\
    - May 17, 2026\\\\
    - <employer>\\\\
    - Location\\\\
    \\\\
    <city> (<province>)\\\\
    \\\\
    Salary\\\\
    <salary text>\\\\
    - Job BankJob number:\\\\
    <id>](https://www.jobbank.gc.ca/jobsearch/jobposting/<id>;jsessionid=...)

A separate "Save to favourites" link gives the clean title:

    [<clean title> - Save to favourites](...#favourite-popup-<id>)

We use the id to correlate the two and parse line-by-line.
"""
from __future__ import annotations
import logging
import re

from src.normalize import make_job, infer_region

log = logging.getLogger(__name__)

BASE_URL = "https://www.jobbank.gc.ca/jobsearch/jobsearch"

# Primary city to use as the searchstring keyword per region.
# More cities per region = better coverage but more credits.
REGION_SEARCH_TERMS = {
    "Hamilton":            ["Hamilton", "Stoney Creek"],
    "Niagara":             ["St. Catharines", "Niagara Falls", "Welland", "Fort Erie"],
    "Brantford":           ["Brantford", "Paris"],
    "Haldimand-Norfolk":   ["Simcoe", "Caledonia", "Dunnville", "Delhi"],
    "Halton":              ["Oakville", "Burlington", "Milton", "Georgetown", "Acton", "Halton Hills"],
}
PAGES_PER_TERM = 3  # ~25 jobs/page; 3 pages = ~75 candidates per term


def _build_search_url(term: str, page: int) -> str:
    from urllib.parse import quote_plus
    return f"{BASE_URL}?searchstring={quote_plus(term)}&sort=D&page={page}"


def fetch(firecrawl_client, pages_per_term: int = PAGES_PER_TERM) -> list[dict]:
    """Scrape Job Bank using one or more city-name searchstrings per region.

    Jobs across all terms are deduplicated by job id.
    """
    if not firecrawl_client:
        log.warning("Firecrawl client not provided — skipping Job Bank source")
        return []

    jobs_by_id: dict[str, dict] = {}
    total_credits = 0
    for region, terms in REGION_SEARCH_TERMS.items():
        for term in terms:
            for page in range(1, pages_per_term + 1):
                url = _build_search_url(term, page)
                total_credits += 1
                log.info("Job Bank: %s '%s' page %d", region, term, page)
                try:
                    result = firecrawl_client.scrape(
                        url,
                        formats=["markdown"],
                        only_main_content=True,
                    )
                    parsed = _parse_listing_markdown(getattr(result, "markdown", "") or "")
                    for j in parsed:
                        # Dedupe by URL across all searchstrings
                        jobs_by_id[j["url"]] = j
                except Exception as e:
                    log.warning("    failed: %s", e)
    log.info("Job Bank: %d unique in-region jobs (%d Firecrawl scrapes)",
             len(jobs_by_id), total_credits)
    return list(jobs_by_id.values())


def _parse_listing_markdown(md: str) -> list[dict]:
    """Extract jobs in our 5 regions from a Job Bank search result page (markdown)."""
    if not md:
        return []

    # 1) Clean titles from "Save to favourites" links, keyed by job id
    fav_re = re.compile(
        r"\[([^\]]+?)\s*-\s*Save to favourites\]\([^)]*#favourite-popup-(\d+)\)"
    )
    titles_by_id: dict[str, str] = {
        m.group(2): m.group(1).strip() for m in fav_re.finditer(md)
    }

    # 2) Each main job posting link (multi-line content)
    main_re = re.compile(
        r"\[\*\*([\s\S]+?)\*\*([\s\S]+?)\]\((https?://www\.jobbank\.gc\.ca/jobsearch/jobposting/(\d+)[^)]*)\)",
        re.DOTALL,
    )

    jobs: list[dict] = []
    seen_ids: set[str] = set()
    for m in main_re.finditer(md):
        bold = m.group(1)
        body = m.group(2)
        raw_url = m.group(3)
        job_id = m.group(4)

        if job_id in seen_ids:
            continue
        seen_ids.add(job_id)

        url = raw_url.split(";jsessionid=")[0].split("?source=")[0]

        title = titles_by_id.get(job_id) or _fallback_title_from_bold(bold)
        if not title:
            continue

        parsed = _parse_body_lines(body)
        location = parsed.get("location", "")
        region = infer_region(location)
        if region == "Other":
            continue  # not in our 5 regions

        jobs.append(make_job(
            title=title,
            employer=parsed.get("employer", ""),
            location=location,
            url=url,
            source="Job Bank",
            date=_normalize_date(parsed.get("date_text", "")) or None,
            salary=parsed.get("salary", "Not listed"),
            region=region,
        ))
    return jobs


def _parse_body_lines(body: str) -> dict:
    """Walk the line-structured body to pull date/employer/location/salary."""
    # Markdown hard-breaks come through as backslashes; replace all runs of \
    # with newlines, then strip leading bullets/spaces.
    clean = re.sub(r"\\+", "\n", body)
    lines = []
    for raw in clean.split("\n"):
        s = raw.strip().lstrip("-").strip()
        if s:
            lines.append(s)

    location_idx = None
    salary_idx = None
    for i, l in enumerate(lines):
        if l == "Location" and location_idx is None:
            location_idx = i
        elif l == "Salary" and salary_idx is None:
            salary_idx = i

    date_text = ""
    for l in lines:
        if re.match(r"^[A-Z][a-z]+ \d{1,2},?\s*\d{4}$", l):
            date_text = l
            break

    employer = ""
    if location_idx is not None and location_idx > 0:
        # The non-date line immediately before "Location" is the employer.
        # Walk backward to skip the date line if it's right there.
        for back in range(location_idx - 1, -1, -1):
            cand = lines[back]
            if cand and not re.match(r"^[A-Z][a-z]+ \d{1,2},?\s*\d{4}$", cand):
                employer = cand
                break

    location = ""
    if location_idx is not None and location_idx + 1 < len(lines):
        location = lines[location_idx + 1]

    salary = "Not listed"
    if salary_idx is not None and salary_idx + 1 < len(lines):
        salary = lines[salary_idx + 1]

    return {
        "date_text": date_text,
        "employer": employer,
        "location": location,
        "salary": salary,
    }


# Source-name prefixes that appear directly before the title in the bold text.
# Used as a fallback when "Save to favourites" doesn't yield a clean title.
_SOURCE_PREFIX_RE = re.compile(
    r".*?(?:Job Bank|indeed\.com|Jobillico|SaskJobs|86network|JobillicoFrancais|"
    r"jobs?\.[a-z0-9]+\.[a-z]{2,3}|[A-Z][a-zA-Z]+\.com)\s*",
    re.IGNORECASE,
)


def _fallback_title_from_bold(bold: str) -> str:
    text = re.sub(r"\s+", " ", bold).strip()
    cleaned = _SOURCE_PREFIX_RE.sub("", text, count=1)
    return cleaned.strip()


def _normalize_date(text: str) -> str:
    """Convert 'May 17, 2026' / 'May 17 2026' to ISO YYYY-MM-DD."""
    if not text:
        return ""
    from datetime import datetime, timedelta
    t = text.strip()
    if t.lower().startswith("today"):
        return datetime.now().date().isoformat()
    if t.lower().startswith("yesterday"):
        return (datetime.now().date() - timedelta(days=1)).isoformat()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(t, fmt).date().isoformat()
        except ValueError:
            continue
    return ""
