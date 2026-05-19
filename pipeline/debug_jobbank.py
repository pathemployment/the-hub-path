"""Dump one Job Bank scrape's raw output for inspection."""
import os
from dotenv import load_dotenv
load_dotenv(".env")
from firecrawl import Firecrawl

client = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])

# Try with explicit province + location params
url = "https://www.jobbank.gc.ca/jobsearch/jobsearch?fctr=Hamilton&fpr=ON&sort=D&page=1"
print(f"Scraping: {url}")
result = client.scrape(url, formats=["markdown", "html"], only_main_content=True)

with open("debug_jobbank_md.txt", "w", encoding="utf-8") as f:
    f.write(result.markdown or "")
with open("debug_jobbank_html.txt", "w", encoding="utf-8") as f:
    f.write(result.html or "")

print(f"Markdown chars: {len(result.markdown or '')}")
print(f"HTML chars: {len(result.html or '')}")
print("Written: debug_jobbank_md.txt, debug_jobbank_html.txt")
print()
print("--- First 2000 chars of markdown ---")
print((result.markdown or "")[:2000])
