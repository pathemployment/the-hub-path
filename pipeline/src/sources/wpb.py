"""Workforce Planning Board scrapers.

Each region in our coverage area has a Workforce Planning Board that
sometimes hosts/lists jobs. Configured in config/wpb_sources.yaml.
"""
from __future__ import annotations
import logging
import re
import yaml
from pathlib import Path
from urllib.parse import urlparse

from src.normalize import make_job

log = logging.getLogger(__name__)


def load_sources(config_dir: Path | str) -> dict:
    path = Path(config_dir) / "wpb_sources.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def fetch(firecrawl_client, sources: dict | None = None,
          config_dir: Path | str | None = None) -> list[dict]:
    if not firecrawl_client:
        log.warning("Firecrawl client not provided — skipping WPB source")
        return []
    if sources is None and config_dir is not None:
        sources = load_sources(config_dir)
    sources = sources or {}

    jobs: list[dict] = []
    for region, info in sources.items():
        url = info.get("url")
        if not url:
            continue
        log.info("WPB scrape: %s -> %s", region, url)
        try:
            scraped = firecrawl_client.scrape(
                url,
                formats=["markdown"],
                only_main_content=True,
            )
            jobs.extend(_parse(scraped, region, info.get("name", "Workforce Planning Board")))
        except Exception as e:
            log.warning("  WPB %s failed: %s", region, e)
    return jobs


def _parse(scrape_result, region: str, source_label: str) -> list[dict]:
    md = getattr(scrape_result, "markdown", None) or ""
    if not md:
        return []

    link_re = re.compile(r"\[([^\]]{4,140})\]\((https?://[^\)]+)\)")
    out: list[dict] = []
    seen: set[str] = set()
    for m in link_re.finditer(md):
        text = m.group(1).strip()
        href = m.group(2).strip()
        if href in seen:
            continue
        if not _looks_like_job_url(href):
            continue
        if _is_nav(text):
            continue
        host = urlparse(href).netloc.lower()
        if not host or _is_wpb_own_domain(host):
            continue
        seen.add(href)
        out.append(make_job(
            title=text,
            employer="",  # unknown from listing; enrichment may resolve
            location=region,
            url=href,
            source=source_label,
            region=region,
        ))
    log.info("  WPB %s: kept %d job-shaped links", region, len(out))
    return out


# Only accept URLs whose path looks like an actual job posting / opening,
# not navigation, social, news, or research links.
_JOB_URL_PATTERNS = [
    "/jobsearch/jobposting/",  # Job Bank
    "/viewjob",                # Indeed
    "/job/",                   # many ATSs
    "/jobs/",                  # generic
    "/position",
    "/posting/",
    "/opening",
    "/vacancy",
    "/employment",
    "/career-opportunit",
    "linkedin.com/jobs/view",
    "glassdoor.",
    "workopolis.",
]


def _looks_like_job_url(url: str) -> bool:
    u = url.lower()
    return any(p in u for p in _JOB_URL_PATTERNS)


# WPB own-domain links are virtually always nav, not job postings.
_WPB_OWN_DOMAINS = {
    "workforceplanninghamilton.ca",
    "niagaraworkforceboard.ca",
    "workforceplanningboard.org",
    "wpb.ca",
}


def _is_wpb_own_domain(host: str) -> bool:
    return any(d in host for d in _WPB_OWN_DOMAINS)


def _is_nav(text: str) -> bool:
    t = text.strip().lower()
    nav_words = {
        "home", "about", "about us", "contact", "contact us", "events",
        "news", "resources", "training", "search", "menu", "more",
        "subscribe", "sign up", "log in", "sign in", "learn more",
        "read more", "click here", "watch video", "watch our video",
        "view all", "view more", "next", "previous",
    }
    return t in nav_words or len(t) < 4
