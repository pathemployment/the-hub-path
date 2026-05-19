"""Common job schema, region inference, and dedup."""
from __future__ import annotations
from datetime import datetime
from typing import Iterable

REGIONS = ["Hamilton", "Niagara", "Brantford", "Haldimand-Norfolk", "Halton"]

EDU_LABELS = {
    "none": "No formal / On-the-job",
    "hs": "High school",
    "college": "College / Trade",
}

# Cities/towns -> region. Order matters; first hit wins.
REGION_KEYWORDS = {
    "Hamilton": [
        "hamilton", "ancaster", "dundas", "stoney creek", "waterdown",
        "flamborough", "binbrook", "mount hope",
    ],
    "Niagara": [
        "niagara", "st. catharines", "st catharines", "welland", "thorold",
        "fort erie", "grimsby", "lincoln", "beamsville", "pelham",
        "wainfleet", "port colborne", "niagara-on-the-lake", "niagara falls",
    ],
    "Brantford": [
        "brantford", "brant ", "burford", "paris on", "paris, on",
        "st. george", "scotland",
    ],
    "Haldimand-Norfolk": [
        "haldimand", "norfolk", "simcoe", "delhi", "port dover", "waterford",
        "caledonia", "dunnville", "cayuga", "hagersville", "jarvis",
        "townsend", "port rowan",
    ],
    "Halton": [
        "halton", "oakville", "burlington", "milton", "georgetown",
        "acton", "halton hills",
    ],
}


def infer_region(location: str) -> str:
    """Map a location string to one of the 5 regions, or 'Other'."""
    loc = (location or "").lower()
    for region, keywords in REGION_KEYWORDS.items():
        if any(kw in loc for kw in keywords):
            return region
    return "Other"


def make_job(
    *,
    title: str,
    employer: str,
    location: str,
    url: str,
    source: str,
    date: str | None = None,
    salary: str = "Not listed",
    description: str = "",
    submitted: bool = False,
    region: str | None = None,
    company_url: str | None = None,
    **extras,
) -> dict:
    """Build a job dict in the canonical schema."""
    title = (title or "").strip()
    employer = (employer or "").strip()
    location = (location or "").strip()
    return {
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "title": title,
        "employer": employer,
        "location": location,
        "url": (url or "").strip(),
        "source": source,
        "salary": (salary or "Not listed").strip() or "Not listed",
        "description": description or "",
        "submitted": bool(submitted),
        "region": region or infer_region(location),
        # Filled by enrich passes; default to None so they're omitted at output.
        "category": extras.get("category"),
        "edu_level": extras.get("edu_level"),
        "edu_label": extras.get("edu_label"),
        "company_url": company_url,
        "transit_accessible": extras.get("transit_accessible"),
        "transit_agency": extras.get("transit_agency"),
        "transit_agency_url": extras.get("transit_agency_url"),
        "tip_resume": extras.get("tip_resume"),
        "tip_cover": extras.get("tip_cover"),
        "client_subject": extras.get("client_subject"),
        "client_body": extras.get("client_body"),
    }


def dedupe(jobs: Iterable[dict]) -> list[dict]:
    """Remove duplicate jobs. Prefer 'submitted' versions when conflicting."""
    seen: dict[str, dict] = {}
    for j in jobs:
        key = (j.get("url") or "").strip().lower()
        if not key:
            key = "|".join([
                (j.get("title") or "").lower(),
                (j.get("employer") or "").lower(),
                (j.get("location") or "").lower(),
            ])
        if key not in seen:
            seen[key] = j
            continue
        # Prefer the submitted version (counsellor-vetted)
        if j.get("submitted") and not seen[key].get("submitted"):
            seen[key] = j
    return list(seen.values())


def filter_recent(jobs: Iterable[dict], window_days: int = 14) -> list[dict]:
    """Drop jobs older than window_days from today."""
    today = datetime.now().date()
    out = []
    for j in jobs:
        try:
            d = datetime.strptime(j.get("date", ""), "%Y-%m-%d").date()
            if (today - d).days <= window_days:
                out.append(j)
        except (ValueError, TypeError):
            # If date is unparseable, include it rather than silently drop
            out.append(j)
    return out
