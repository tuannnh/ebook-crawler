import requests
import yaml
from bs4 import BeautifulSoup

with open("config.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

headers = {"User-Agent": config["http"]["user_agents"][0]}
verify = config["http"].get("verify_ssl", True)

BOOK_URL = "https://truyenfull.vision/dich-thi-thien-dao/"

print("=== BOOK PAGE ===")
r = requests.get(BOOK_URL, headers=headers, timeout=30, verify=verify)
print("Status:", r.status_code)
soup = BeautifulSoup(r.text, "lxml")

print("title h3.title:", soup.select_one("h3.title"))
print("author:", soup.select_one('.info-holder .info a[itemprop="author"]'))
print("description:", str(soup.select_one('div[itemprop="description"]'))[:120] if soup.select_one('div[itemprop="description"]') else None)
print("cover:", soup.select_one(".book img"))

chapters = soup.select("ul.list-chapter li a")
print(f"\nChapter links on page 1: {len(chapters)}")
for a in chapters[:5]:
    print(f"  {a.get_text(strip=True)} -> {a['href']}")

pagination = soup.select_one("ul.pagination li:last-child a")
print("\nNext page link:", pagination["href"] if pagination else None)

# Fetch first chapter to verify content selector
if chapters:
    first_url = chapters[0]["href"]
    print(f"\n=== CHAPTER PAGE: {first_url} ===")
    rc = requests.get(first_url, headers=headers, timeout=30, verify=verify)
    sc = BeautifulSoup(rc.text, "lxml")
    content = sc.select_one("div#chapter-c")
    if content:
        for tag in content.select("div.ads-holder, script, style"):
            tag.decompose()
        text = content.get_text("\n", strip=True)
        print(f"Content length: {len(text)} chars")
        print("First 300 chars:", text[:300])
    else:
        print("div#chapter-c NOT FOUND")
        print("Available divs with id:", [d["id"] for d in sc.select("div[id]")][:10])
