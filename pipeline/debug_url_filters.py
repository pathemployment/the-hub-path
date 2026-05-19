"""Probe which Job Bank URL parameter actually filters by location."""
import os
import re
from dotenv import load_dotenv
load_dotenv(".env")
from firecrawl import Firecrawl

client = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])

variants = [
    ("fpr=ON only",                 "https://www.jobbank.gc.ca/jobsearch/jobsearch?fpr=ON&sort=D&page=1"),
    ("searchstring=Hamilton",       "https://www.jobbank.gc.ca/jobsearch/jobsearch?searchstring=Hamilton&sort=D&page=1"),
    ("locationstring=Hamilton,+ON", "https://www.jobbank.gc.ca/jobsearch/jobsearch?locationstring=Hamilton%2C+ON&sort=D&page=1"),
    ("flocation=Hamilton",          "https://www.jobbank.gc.ca/jobsearch/jobsearch?flocation=Hamilton&sort=D&page=1"),
]

print(f"{'variant':30} | {'total results':15} | {'Hamilton-ON hits on page'}")
print("-" * 80)
for label, url in variants:
    try:
        r = client.scrape(url, formats=["markdown"], only_main_content=True)
        md = r.markdown or ""
        total_m = re.search(r"##\s*([\d,]+)\s*results", md)
        total = total_m.group(1) if total_m else "?"
        hamilton_hits = len(re.findall(r"Hamilton \(ON\)", md))
        st_cath_hits = len(re.findall(r"St\. Catharines \(ON\)", md))
        other_ontario_cities = len(re.findall(r"\(ON\)", md))
        print(f"{label:30} | {total:15} | Hamilton: {hamilton_hits}, St.Cath: {st_cath_hits}, total-ON: {other_ontario_cities}")
    except Exception as e:
        print(f"{label:30} | ERROR: {e}")
