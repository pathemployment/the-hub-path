"""Transit accessibility lookup.

v1 = lightweight heuristic only:
  - If the job location is in a region's "core city", assume bus-accessible.
  - Otherwise mark car_needed.

v2 (later) = real GTFS lookup: download each agency's GTFS feed, geocode the
job location, find nearest stop, check distance ≤ 800m (~10 min walk).

Stubbing v1 lets the UI show transit indicators today; v2 swaps in without
touching anything else.
"""
from __future__ import annotations
import yaml
from pathlib import Path

_AGENCIES_CACHE: dict | None = None


def load_agencies(config_dir: Path | str) -> dict:
    global _AGENCIES_CACHE
    if _AGENCIES_CACHE is not None:
        return _AGENCIES_CACHE
    path = Path(config_dir) / "transit_agencies.yaml"
    with open(path, "r", encoding="utf-8") as f:
        _AGENCIES_CACHE = yaml.safe_load(f) or {}
    return _AGENCIES_CACHE


# Core-city heuristic: locations matching these strings are considered
# bus-accessible by default. Rural addresses fall through to car_needed.
_CORE_CITY_KEYWORDS = {
    "Hamilton": ["hamilton", "stoney creek", "dundas", "ancaster"],
    "Niagara": ["st. catharines", "st catharines", "niagara falls", "welland", "thorold", "fort erie"],
    "Brantford": ["brantford"],
    "Haldimand-Norfolk": ["simcoe", "caledonia", "dunnville"],
    "Halton": ["oakville", "burlington", "milton", "georgetown"],
}


def enrich(job: dict, agencies: dict) -> dict:
    """Add transit fields to a job dict in place.

    For accessible jobs, the transit_agency_url is a Google Maps DIRECTIONS
    URL to the job location with travelmode=transit. Clicking it gives the
    user actual transit routing to that employer, not just the agency's HQ.
    """
    from urllib.parse import quote_plus

    region = job.get("region", "Other")
    location = (job.get("location") or "").lower()
    region_agencies = agencies.get(region, {})

    # Default: unknown
    job["transit_accessible"] = None
    job["transit_agency"] = None
    job["transit_agency_url"] = None

    if region == "Other" or not region_agencies:
        return job

    # Core city heuristic
    core_keywords = _CORE_CITY_KEYWORDS.get(region, [])
    if any(kw in location for kw in core_keywords):
        agency_name = region_agencies.get("primary_name")
        # Build a Google Maps directions URL to the job's actual location
        employer = (job.get("employer") or "").strip()
        loc = (job.get("location") or "").strip()
        # Prefer "<employer> <city>" so Google resolves to the business address
        if employer and loc:
            destination = f"{employer} {loc}"
        elif employer:
            destination = employer
        elif loc:
            destination = loc
        else:
            destination = ""
        if destination:
            url = ("https://www.google.com/maps/dir/?api=1"
                   f"&destination={quote_plus(destination)}"
                   "&travelmode=transit")
        else:
            url = ""
        job["transit_accessible"] = True
        job["transit_agency"] = agency_name
        job["transit_agency_url"] = url
    else:
        job["transit_accessible"] = False

    return job
