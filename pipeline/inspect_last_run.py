"""Quick inspection of data/jobs-test.js after a pipeline run."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

path = Path("data/jobs-test.js")
if not path.exists():
    print(f"No file at {path} — run the pipeline first.")
    sys.exit(1)

content = path.read_text(encoding="utf-8")
match = re.search(r"window\.HUB_JOBS = (\[[\s\S]*?\]);\s*$", content, re.M)
if not match:
    print("Could not find HUB_JOBS array in file.")
    sys.exit(1)

jobs = json.loads(match.group(1))
print(f"Total jobs: {len(jobs)}")
print()

print("By region:")
for region, n in Counter(j.get("region", "?") for j in jobs).most_common():
    print(f"  {region:20} {n}")

print()
print("By cluster:")
for cat, n in Counter(j.get("category", "?") for j in jobs).most_common():
    print(f"  {cat:25} {n}")

print()
print("By education level:")
for edu, n in Counter(j.get("edu_level", "?") for j in jobs).most_common():
    print(f"  {edu:10} {n}")

print()
print("Transit accessibility:")
bus = sum(1 for j in jobs if j.get("transit_accessible") is True)
car = sum(1 for j in jobs if j.get("transit_accessible") is False)
none = sum(1 for j in jobs if j.get("transit_accessible") is None)
print(f"  bus-accessible: {bus}")
print(f"  car-needed:     {car}")
print(f"  unknown:        {none}")

print()
print("Sample of 8 jobs (random-ish):")
step = max(1, len(jobs) // 8)
for j in jobs[::step][:8]:
    title = (j.get("title") or "")[:40]
    employer = (j.get("employer") or "")[:25]
    location = (j.get("location") or "")[:22]
    region = j.get("region", "?")
    cat = j.get("category", "?")[:22]
    sal = (j.get("salary") or "?")[:15]
    print(f"  - {title:40} | {employer:25} | {location:22} | {region:18} | {cat:22} | {sal}")
