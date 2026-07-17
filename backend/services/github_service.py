import requests
from config import settings
from services import storage

GITHUB_API = "https://api.github.com"


def _headers():
    headers = {}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"
    return headers


def _fetch_readme(full_name: str) -> str:
    try:
        resp = requests.get(
            f"{GITHUB_API}/repos/{full_name}/readme",
            headers={**_headers(), "Accept": "application/vnd.github.raw"},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.text
        return ""
    except requests.RequestException:
        return ""


def _fetch_top_level_files(full_name: str) -> list:
    try:
        resp = requests.get(
            f"{GITHUB_API}/repos/{full_name}/contents/",
            headers=_headers(),
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        entries = resp.json()
        if not isinstance(entries, list):
            return []
        return [e.get("name", "") for e in entries[:20]]
    except requests.RequestException:
        return []


def fetch_github_context(gemini) -> dict:
    if not settings.github_username:
        return {"summary": "No GitHub username configured.", "repo_names": []}

    try:
        resp = requests.get(
            f"{GITHUB_API}/users/{settings.github_username}/repos",
            params={"sort": "updated", "per_page": 100},
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        repos = resp.json()
    except requests.RequestException:
        return {"summary": "Could not fetch GitHub data.", "repo_names": []}

    repos = [r for r in repos if not r.get("fork")]
    repos.sort(key=lambda r: r.get("stargazers_count", 0), reverse=True)
    top_repos = repos[:6]

    lines = []
    repo_names = []
    for r in top_repos:
        name = r.get("name", "")
        full_name = r.get("full_name", "")
        lang = r.get("language") or "unspecified"
        stars = r.get("stargazers_count", 0)
        pushed_at = r.get("pushed_at", "")

        description = storage.get_cached_repo_analysis(full_name, pushed_at)
        if not description:
            readme_text = _fetch_readme(full_name)
            file_names = _fetch_top_level_files(full_name)
            try:
                description = gemini.analyze_repo(name, readme_text, file_names)
            except Exception:
                description = r.get("description") or "No description available."
            storage.save_repo_analysis(full_name, pushed_at, description)

        lines.append(f"- {name} ({lang}, {stars} stars): {description}")
        repo_names.append(name)

    if not lines:
        return {"summary": "No public repositories found.", "repo_names": []}

    return {
        "summary": "Top GitHub projects:\n" + "\n".join(lines),
        "repo_names": repo_names,
    }