"""Template-based resume + cover-letter tip enrichment.

Loads tip_templates.yaml and assigns each job the (resume, cover) pair that
matches its cluster + education level. No API, no recurring cost.

If a job has no category yet (run classify.enrich first) or has an unknown
cluster, falls back to the cluster's 'Other' templates or the global default.
"""
from __future__ import annotations
import logging
import yaml
from pathlib import Path

log = logging.getLogger(__name__)

_TEMPLATES_CACHE: dict | None = None


def load_templates(config_dir: Path | str) -> dict:
    global _TEMPLATES_CACHE
    if _TEMPLATES_CACHE is not None:
        return _TEMPLATES_CACHE
    path = Path(config_dir) / "tip_templates.yaml"
    with open(path, "r", encoding="utf-8") as f:
        _TEMPLATES_CACHE = yaml.safe_load(f) or {}
    return _TEMPLATES_CACHE


def enrich_one(job: dict, templates: dict) -> dict:
    """Set tip_resume + tip_cover from the template library."""
    cluster = job.get("category") or "Other"
    edu = job.get("edu_level") or "none"

    cluster_block = templates.get(cluster) or templates.get("Other") or {}
    edu_block = cluster_block.get(edu) if isinstance(cluster_block, dict) else None
    if not edu_block:
        edu_block = templates.get("_default") or {}

    job["tip_resume"] = edu_block.get("resume", "")
    job["tip_cover"] = edu_block.get("cover", "")
    return job


def enrich_all(jobs: list[dict], config_dir: Path | str | None = None) -> list[dict]:
    """Enrich every job in place."""
    if config_dir is None:
        config_dir = Path(__file__).resolve().parent.parent.parent / "config"
    templates = load_templates(config_dir)
    for j in jobs:
        enrich_one(j, templates)
    log.info("Tip enrichment applied to %d jobs (template-based, no API)", len(jobs))
    return jobs
