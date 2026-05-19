"""Rule-based scam filter. Returns True if a job should be EXCLUDED."""
from __future__ import annotations
import re

# Phrases that strongly suggest a scam in entry-level postings.
SCAM_PHRASES = [
    "work from home no experience",
    "earn $1000",
    "earn $2000",
    "earn $3000",
    "no experience required, earn",
    "be your own boss",
    "weekly pay direct to your bank",
    "send your bank info",
    "send your sin",
    "send your social insurance",
    "registration fee",
    "training fee",
    "starter kit fee",
    "pay to start",
    "must purchase",
    "must buy",
    "telegram me",
    "whatsapp me",
    "text me at",
    "reply to my gmail",
]

# Generic free-email domains as the ONLY contact — suspicious for legit employers
FREE_EMAIL_DOMAINS = ["@gmail.com", "@yahoo.com", "@hotmail.com", "@outlook.com", "@aol.com", "@protonmail.com"]


def is_scam(job: dict, market_max_hourly: float = 35.0) -> tuple[bool, str]:
    """Return (is_scam, reason). reason is empty if not a scam.

    Government-listed jobs (source == 'Job Bank') skip wage and employer
    checks since Job Bank vets postings before publishing.
    """
    source = job.get("source", "")
    text = " ".join([
        job.get("title", ""),
        job.get("employer", ""),
        job.get("description", ""),
        job.get("salary", ""),
    ]).lower()

    # Phrase-based check applies to all sources
    for phrase in SCAM_PHRASES:
        if phrase in text:
            return True, f"matched scam phrase: '{phrase}'"

    # Skip the rest of the heuristics for vetted sources
    if source in ("Job Bank", "Submitted"):
        return False, ""

    # Asks to contact a free-email domain with no employer website
    if not job.get("company_url"):
        contacts = re.findall(r"[\w\.-]+@[\w\.-]+", text)
        if contacts and all(any(d in c for d in FREE_EMAIL_DOMAINS) for c in contacts):
            return True, "only free-email contact, no employer website"

    # Implausibly high wage (catches '$5000/week typing from home' patterns)
    # Threshold is generous (5x market) so we don't catch real skilled-trade rates.
    wage = _parse_hourly_wage(job.get("salary", ""))
    if wage and wage > market_max_hourly * 5:
        return True, f"hourly wage ${wage:.2f} implausibly high"

    # Empty employer field
    if not job.get("employer") or job.get("employer").lower() in {"private", "confidential", "n/a"}:
        return True, "no identifiable employer"

    return False, ""


def _parse_hourly_wage(salary: str) -> float | None:
    """Pull an hourly wage from text like '$18.50 / hour' or '18.50/hr'. Returns None if not hourly."""
    if not salary:
        return None
    s = salary.lower()
    if not any(t in s for t in ["hour", "/hr", " hr", "hourly"]):
        return None
    m = re.search(r"\$?\s*(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _is_skilled_trade(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in [
        "electrician", "plumber", "welder", "millwright", "machinist",
        "carpenter", "hvac", "mechanic", "tool and die",
    ])
