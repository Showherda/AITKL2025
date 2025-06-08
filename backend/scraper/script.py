import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from fake_useragent import UserAgent
from collections import deque
import time
import json
from google import genai
import dotenv
import os
import json

# Load environment variables from .env file
dotenv.load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# response = client.models.generate_content(
#     model="gemini-2.0-flash",
#     contents="Explain how AI works in a few words",
# )

# {
#     "logo": "url to logo",
#     "name": "company's name",
#     "company_description": "short description of the company",
#     "summary": "one line short company description",
#     "status": "active/inactive so 1 or 0",
#     "website_url": "url to website",
#     "founding_year": "year",
#     "startup_category": "the sector or industry the startup operates in",
#     "founding_team_size": "number of founding team members",
#     "magic_accredited": "true/false",
#     "employees": [
#         {
#             "name": "Employee A (example name)",
#             "title": "Role",
#             "linkedin_url": "https://linkedin.com/in/example"
#         }
#     ],
#     "location": "Kuala Lumpur, Malaysia (example location)",
#     "founder": {
#         "name": "John Doe",
#         "photo": "url_to_photo",
#         "linkedin_url": "https://linkedin.com/in/founder",
#         "email": "john@example.com",
#         "phone_number": "+60-xxx-xxx"
#     }
# }


ua = UserAgent()

BAD_PATTERNS = ['calendar', 'page=', 'sort=', 'session=', 'filter=', 'lang=', 'utm_']
MAX_PAGES = 50
MAX_DEPTH = 3
CRAWL_DELAY = 0.5  # seconds
REQUIRED_FIELDS = {
    "logo", "name", "company description", "summary", "status",
    "website url", "founding year", "startup category", "founding team size",
    "magic accredited", "employees", "location", "founder"
}
output = {}

def get_domain(url):
    return urlparse(url).netloc

def normalize_url(url):
    parsed = urlparse(url)
    clean_path = parsed.path.rstrip('/')
    return urlunparse((parsed.scheme, parsed.netloc, clean_path, '', '', ''))

def is_internal_link(link, domain):
    parsed = urlparse(link)
    return parsed.netloc == '' or parsed.netloc == domain

def is_valid_url(url):
    url = url.lower()
    return not any(p in url for p in BAD_PATTERNS)

def clean_text(soup):
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    return ' '.join(soup.get_text(separator=' ', strip=True).split())

def extract_links(soup, base_url, domain):
    links = set()
    for tag in soup.find_all('a', href=True):
        href = urljoin(base_url, tag['href'])
        if is_internal_link(href, domain) and is_valid_url(href):
            links.add(normalize_url(href))
    return links

def scrape_page(url):
    headers = {'User-Agent': ua.random}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if 'text/html' not in res.headers.get('Content-Type', ''):
            return None
        soup = BeautifulSoup(res.text, 'html.parser')
        return {
            "url": url,
            "text": clean_text(soup),
            "links": list(extract_links(soup, url, get_domain(url)))
        }
    except Exception as e:
        print(f"[ERROR] {url}: {e}")
        return None

def crawl_domain(start_url):
    domain = get_domain(start_url)
    visited = set()
    queue = deque([(normalize_url(start_url), 0)])
    results = []

    while queue and len(visited) < MAX_PAGES:
        url, depth = queue.popleft()
        if url in visited or depth > MAX_DEPTH:
            continue

        print(f"[Crawling] {url} (depth {depth})")
        visited.add(url)
        page_data = scrape_page(url)
        if page_data:
            results.append(page_data)
            for link in page_data['links']:
                if link not in visited:
                    queue.append((link, depth + 1))
        time.sleep(CRAWL_DELAY)

    return results

def gemini_extract_fields(text, links):
    """Send data to Gemini and extract required fields."""
    prompt = f"""
Given the following text and links from a startup's website, extract the following fields in JSON format:
{{
    "logo": "url to logo",
    "name": "company's name",
    "company_description": "short description of the company",
    "summary": "one line short company description",
    "status": "active/inactive so 1 or 0",
    "website_url": "url to website",
    "founding_year": "year",
    "startup_category": "the sector or industry the startup operates in",
    "founding_team_size": "number of founding team members",
    "magic_accredited": "true/false",
    "employees": [
        {{
            "name": "Employee A (example name)",
            "title": "Role",
            "linkedin_url": "https://linkedin.com/in/example"
        }}
    ],
    "location": "Kuala Lumpur, Malaysia (example location)",
    "founder": {{
        "name": "John Doe",
        "photo": "url to photo",
        "linkedin_url": "https://linkedin.com/in/founder",
        "email": "john@example.com",
        "phone_number": "+60-xxx-xxx"
    }}
}}
follow this exact format, do not add any other fields or change the names of the fields. if you cannot find a field, set it to null or an empty string.
Please ensure the output is valid JSON. The values in the format JSON are all examples, do not use them in your output.

TEXT:
{text[:3000]}

LINKS:
{links}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"[Gemini Error] {e}")
        return None

def update_output(gemini_json):
    import json, re
    try:
        # Clean up common errors like markdown backticks
        cleaned = gemini_json.strip().removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(cleaned)
        for key, value in parsed.items():
            if key not in output or not output[key]:
                output[key] = value
    except Exception as e:
        print(f"[Parse Error] {e}")
        print("[DEBUG] Raw Gemini response:")
        print(gemini_json[:300])

def is_output_complete():
    return all(key in output and output[key] for key in REQUIRED_FIELDS)

def crawl_until_complete(start_url):
    global output
    output = {}
    domain = get_domain(start_url)
    visited = set()
    queue = deque([(normalize_url(start_url), 0)])
    page_count = 0

    while queue and page_count < MAX_PAGES and not is_output_complete():
        url, depth = queue.popleft()
        if url in visited or depth > MAX_DEPTH:
            continue

        print(f"[Crawling] {url} (depth {depth})")
        visited.add(url)
        page_data = scrape_page(url)
        if not page_data:
            continue

        print(f"  → Extracting with Gemini...")
        response = gemini_extract_fields(page_data["text"], page_data["links"])
        if response:
            update_output(response)

        for link in page_data["links"]:
            if link not in visited:
                queue.append((link, depth + 1))

        page_count += 1
        time.sleep(CRAWL_DELAY)

    print("\n✅ Crawl complete.")
    print(f"Pages crawled: {page_count}")
    print(f"Fields extracted: {len([k for k in output if output[k]])} / {len(REQUIRED_FIELDS)}")
    return output

start_urls = [
    "https://www.tanoticraft.com/",
    "https://www.eatxdignity.com/",
    "https://www.urbanhijau.com/",
    "https://www.pichaproject.com/",
    "https://www.komunititukangjahit.com/",
    "https://www.sols247.org/",
    "https://www.theasli.co/",
    "https://www.epichome.org/",
]

# row number 18 done, only 1 and 2 have been crawled actually

# Example usage
if __name__ == "__main__":
    for start_url in start_urls:
        print(f"\n🔍 Starting crawl for: {start_url}")
        final_output = crawl_until_complete(start_url)

        with open("structured_output.json", "a", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False)
            f.write("\n")  # Newline for each entry

        print("📁 Output saved to structured_output.json")
