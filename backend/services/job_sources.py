import html
import re
import requests
from config import settings

def clean_description(raw_desc: str) -> str:
    if not raw_desc:
        return ""
    desc = html.unescape(raw_desc)
    desc = html.unescape(desc)
    return desc


# Greenhouse and Lever expose public, TOS-friendly JSON endpoints for
# companies that host their job boards on them. Adzuna and Arbeitnow are
# legitimate aggregator APIs with their own free tiers. None of this
# scrapes LinkedIn/Indeed directly - both actively block that and can ban
# accounts for it, so we stick to sources that offer real API access.

GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
LEVER_URL = "https://api.lever.co/v0/postings/{company}"
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"

REMOTE_KEYWORDS = ["remote", "work from home", "wfh", "distributed team"]
HYBRID_KEYWORDS = ["hybrid"]

# Best-effort compensation extraction for sources that don't give structured
# salary data (Greenhouse/Lever/Arbeitnow rarely do). Looks for common
# currency-prefixed number patterns in the description text. This will miss
# a lot and occasionally mis-grab an unrelated number - it's a starting
# point to scan quickly, not something to trust blindly.
COMPENSATION_PATTERN = re.compile(
    r"(?:\$|₹|€|£)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:k|K))?"
    r"(?:\s?(?:-|to|–)\s?(?:\$|₹|€|£)?\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:k|K))?)?"
)


def classify_remote_type(title: str, location: str, description: str) -> str:
    blob = f"{title} {location} {description}".lower()
    if any(kw in blob for kw in HYBRID_KEYWORDS):
        return "hybrid"
    if any(kw in blob for kw in REMOTE_KEYWORDS):
        return "remote"
    return "onsite"


def extract_compensation_from_text(text: str) -> str:
    if not text:
        return "Not specified"
    match = COMPENSATION_PATTERN.search(text)
    return match.group(0) if match else "Not specified"


def fetch_greenhouse_jobs(board_token: str) -> list:
    url = GREENHOUSE_URL.format(board=board_token)
    try:
        resp = requests.get(url, params={"content": "true"}, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("jobs", [])
    except requests.RequestException:
        return []

    jobs = []
    for j in data:
        title = j.get("title", "")
        location = (j.get("location") or {}).get("name", "")
        description = clean_description(j.get("content", ""))
        jobs.append({
            "source": "greenhouse",
            "company": board_token,
            "title": title,
            "location": location,
            "description": description,
            "apply_url": j.get("absolute_url", ""),
            "remote_type": classify_remote_type(title, location, description),
            "compensation": extract_compensation_from_text(description),
        })
    return jobs


def fetch_lever_jobs(company: str) -> list:
    url = LEVER_URL.format(company=company)
    try:
        resp = requests.get(url, params={"mode": "json"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return []

    jobs = []
    for j in data:
        title = j.get("text", "")
        location = (j.get("categories") or {}).get("location", "")
        description = clean_description(j.get("descriptionPlain", ""))
        jobs.append({
            "source": "lever",
            "company": company,
            "title": title,
            "location": location,
            "description": description,
            "apply_url": j.get("applyUrl", ""),
            "remote_type": classify_remote_type(title, location, description),
            "compensation": extract_compensation_from_text(description),
        })
    return jobs


def fetch_adzuna_jobs(country: str, keywords: str = "", location: str = "") -> list:
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        return []

    url = ADZUNA_URL.format(country=country)
    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "results_per_page": 50,
        "content-type": "application/json",
    }
    if keywords:
        params["what"] = keywords
    if location:
        params["where"] = location

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("results", [])
    except requests.RequestException:
        return []

    jobs = []
    for j in data:
        title = j.get("title", "")
        loc = (j.get("location") or {}).get("display_name", "")
        description = clean_description(j.get("description", ""))

        salary_min = j.get("salary_min")
        salary_max = j.get("salary_max")
        if salary_min and salary_max:
            compensation = f"{salary_min:,.0f} - {salary_max:,.0f}"
        elif salary_min:
            compensation = f"{salary_min:,.0f}+"
        else:
            compensation = extract_compensation_from_text(description)

        jobs.append({
            "source": f"adzuna-{country}",
            "company": (j.get("company") or {}).get("display_name", "Unknown"),
            "title": title,
            "location": loc,
            "description": description,
            "apply_url": j.get("redirect_url", ""),
            "remote_type": classify_remote_type(title, loc, description),
            "compensation": compensation,
        })
    return jobs


def fetch_arbeitnow_jobs() -> list:
    try:
        resp = requests.get(ARBEITNOW_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except requests.RequestException:
        return []

    jobs = []
    for j in data:
        title = j.get("title", "")
        location = j.get("location", "") or ("Remote" if j.get("remote") else "")
        description = clean_description(j.get("description", ""))

        jobs.append({
            "source": "arbeitnow",
            "company": j.get("company_name", "Unknown"),
            "title": title,
            "location": location,
            "description": description,
            "apply_url": j.get("url", ""),
            "remote_type": "remote" if j.get("remote") else classify_remote_type(title, location, description),
            "compensation": extract_compensation_from_text(description),
        })
    return jobs


def fetch_remoteok_jobs() -> list:
    headers = {"User-Agent": "JobSwiper/1.0"}
    try:
        resp = requests.get("https://remoteok.com/api", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        data = data[1:] if isinstance(data, list) and len(data) > 1 else []
    except Exception:
        return []

    jobs = []
    for j in data[:35]:
        title = j.get("position", "")
        company = j.get("company", "Unknown")
        location = j.get("location", "") or "Remote"
        description = j.get("description", "")
        url = j.get("url", "") or f"https://remoteok.com/remote-jobs/{j.get('id', '')}"
        tags = ", ".join(j.get("tags", []))
        full_desc = f"{description} Tags: {tags}"

        jobs.append({
            "source": "remoteok",
            "company": company,
            "title": title,
            "location": location,
            "description": full_desc,
            "apply_url": url,
            "remote_type": "remote",
            "compensation": extract_compensation_from_text(full_desc),
        })
    return jobs


DEFAULT_GREENHOUSE_BOARDS = ["stripe", "cloudflare", "gitlab", "vercel", "linear", "supabase", "datadog", "figma", "notion"]
DEFAULT_LEVER_COMPANIES = ["airbnb", "netflix", "spotify", "postman"]


def aggregate_jobs(keywords: str = "", location: str = "", remote_type: str = "", country: str = "") -> list:
    jobs = []

    gh_boards = list(set(settings.greenhouse_board_tokens + DEFAULT_GREENHOUSE_BOARDS))
    for board in gh_boards:
        jobs.extend(fetch_greenhouse_jobs(board))

    lever_comps = list(set(settings.lever_companies + DEFAULT_LEVER_COMPANIES))
    for company in lever_comps:
        jobs.extend(fetch_lever_jobs(company))

    adzuna_countries = [country] if country else settings.adzuna_countries
    for c in adzuna_countries:
        jobs.extend(fetch_adzuna_jobs(c, keywords=keywords, location=location))

    jobs.extend(fetch_arbeitnow_jobs())
    jobs.extend(fetch_remoteok_jobs())

    try:
        from services.firecrawl_service import fetch_linkedin_firecrawl_jobs
        jobs.extend(fetch_linkedin_firecrawl_jobs(keywords=keywords, location=location))
    except Exception:
        pass

    if keywords:
        kw = keywords.lower()
        jobs = [j for j in jobs if kw in j["title"].lower() or kw in j["description"].lower() or j["source"].endswith("-firecrawl")]
    if location:
        loc = location.lower()
        jobs = [j for j in jobs if loc in j["location"].lower() or j["source"].startswith("adzuna") or j["source"].endswith("-firecrawl")]
    if remote_type and remote_type != "any":
        jobs = [j for j in jobs if j["remote_type"] == remote_type]

    return jobs