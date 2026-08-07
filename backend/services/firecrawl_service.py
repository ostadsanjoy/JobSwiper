import os
import requests
import re
import html
from config import settings


FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v1/search"


def _get_firecrawl_headers() -> dict:
    api_key = settings.firecrawl_api_key or os.getenv("FIRECRAWL_API_KEY", "")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def fetch_firecrawl_multi_board_jobs(keywords: str = "", location: str = "") -> list:
    api_key = settings.firecrawl_api_key or os.getenv("FIRECRAWL_API_KEY", "")
    if not api_key:
        return []

    sites_query = "site:linkedin.com/jobs/view OR site:indeed.com/viewjob OR site:naukri.com/job-listings OR site:wellfound.com/jobs"
    query = f"({sites_query}) {keywords} {location}".strip()
    try:
        resp = requests.post(
            FIRECRAWL_SEARCH_URL,
            headers=_get_firecrawl_headers(),
            json={"query": query, "limit": 15},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        search_results = resp.json().get("data", [])
    except Exception:
        return []

    from services.job_sources import classify_remote_type, extract_compensation_from_text

    jobs = []
    for item in search_results:
        url = item.get("url", "")
        if not url:
            continue

        raw_desc = html.unescape(item.get("markdown", "") or item.get("description", "") or item.get("snippet", ""))
        raw_desc = html.unescape(raw_desc)

        raw_title = item.get("title", "")

        board_name = "Job Posting"
        if "linkedin.com" in url:
            board_name = "LinkedIn"
        elif "indeed.com" in url:
            board_name = "Indeed"
        elif "naukri.com" in url:
            board_name = "Naukri"
        elif "wellfound.com" in url:
            board_name = "Wellfound"

        company = f"{board_name} Employer"
        title = raw_title

        for suffix in [" | LinkedIn", " - LinkedIn", " | Indeed", " - Indeed", " - Naukri.com", " - Wellfound", " | Wellfound"]:
            title = title.replace(suffix, "")

        if " hiring " in title.lower():
            parts = re.split(r"\s+hiring\s+", title, flags=re.IGNORECASE)
            company = parts[0].strip()
            title = parts[1].split(" in ")[0].strip() if len(parts) > 1 else title
        elif " - " in title:
            parts = title.split(" - ")
            title = parts[0].strip()
            if len(parts) > 1:
                company = parts[1].strip()

        remote_type = classify_remote_type(title, location, raw_desc)
        comp = extract_compensation_from_text(raw_desc)

        jobs.append({
            "source": f"{board_name.lower()}-firecrawl",
            "company": company or f"{board_name} Employer",
            "title": title or "Software Position",
            "location": location or "Remote / Onsite",
            "description": raw_desc or f"{board_name} Job Posting: {url}",
            "apply_url": url,
            "remote_type": remote_type,
            "compensation": comp,
        })

    return jobs


fetch_linkedin_firecrawl_jobs = fetch_firecrawl_multi_board_jobs
