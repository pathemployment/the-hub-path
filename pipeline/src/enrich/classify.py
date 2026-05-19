"""Cluster classification + education inference. Keyword-based, no LLM."""
from __future__ import annotations
import yaml
from pathlib import Path

# Education keyword rules
_HS = [
    "high school diploma", "high school education", "highschool diploma",
    "ossd", "grade 12", "secondary school",
]
_COLLEGE = [
    "college diploma", "college certificate", "post-secondary",
    "postsecondary", "associate degree", "bachelor", "university degree",
    "apprentice", "apprenticeship", "red seal", "trade certificate",
]


def infer_education(text: str) -> tuple[str, str]:
    """Return (edu_level, edu_label). One of: none/hs/college."""
    t = (text or "").lower()
    if any(k in t for k in _COLLEGE):
        return "college", "College / Trade"
    if any(k in t for k in _HS):
        return "hs", "High school"
    return "none", "No formal / On-the-job"


# Cluster rules are loaded from config/cluster_rules.yaml.
# Each cluster maps to a list of substring keywords found in the title.
_CLUSTER_RULES_CACHE: dict[str, list[str]] | None = None


def load_cluster_rules(config_dir: Path | str) -> dict[str, list[str]]:
    global _CLUSTER_RULES_CACHE
    if _CLUSTER_RULES_CACHE is not None:
        return _CLUSTER_RULES_CACHE
    path = Path(config_dir) / "cluster_rules.yaml"
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _CLUSTER_RULES_CACHE = {k: [s.lower() for s in v] for k, v in data.items()}
    return _CLUSTER_RULES_CACHE


def infer_cluster(title: str, description: str, rules: dict[str, list[str]]) -> str:
    """Return the best-matching cluster, or 'Other'."""
    text = ((title or "") + " " + (description or "")).lower()
    best, best_score = "Other", 0
    for cluster, keywords in rules.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best, best_score = cluster, score
    return best


def enrich(job: dict, rules: dict[str, list[str]]) -> dict:
    """Add edu_level, edu_label, category to a job dict in place."""
    text = " ".join([job.get("title", ""), job.get("description", "")])
    edu_level, edu_label = infer_education(text)
    job["edu_level"] = edu_level
    job["edu_label"] = edu_label
    job["category"] = infer_cluster(job.get("title", ""), job.get("description", ""), rules)
    return job
