"""Apply the new strict job-URL filter to the existing employer cache.

Junk entries (image alt text, page titles, accessibility widgets, etc.)
get dropped. Real job postings stay. No Firecrawl credits used.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from src.sources.employers import _looks_like_job_url, _looks_like_job_title

cache_file = Path("data/employer_cache.json")
if not cache_file.exists():
    print(f"No cache file at {cache_file}")
    sys.exit(1)

data = json.loads(cache_file.read_text(encoding="utf-8"))
old_jobs = data.get("jobs", [])

kept = []
for j in old_jobs:
    if _looks_like_job_url(j.get("url", "")) and _looks_like_job_title(j.get("title", "")):
        kept.append(j)

data["jobs"] = kept
cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"Cleaned employer cache:")
print(f"  Before: {len(old_jobs)} entries")
print(f"  After:  {len(kept)} entries")
print(f"  Dropped: {len(old_jobs) - len(kept)} junk entries")
print()
print("Sample of kept entries:")
for j in kept[:10]:
    title = (j.get("title") or "")[:50]
    employer = (j.get("employer") or "")[:30]
    print(f"  - {title:50} | {employer}")
