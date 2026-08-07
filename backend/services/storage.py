import sqlite3
import json
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "job_swiper.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS resume_store (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            resume_text TEXT,
            source_filename TEXT,
            uploaded_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            company TEXT,
            title TEXT,
            location TEXT,
            compensation TEXT,
            status TEXT,
            apply_url TEXT,
            resume_text TEXT,
            cover_letter TEXT,
            github_repos TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS repo_analysis (
            repo_full_name TEXT PRIMARY KEY,
            pushed_at TEXT,
            description TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS profile_store (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            full_name TEXT,
            email TEXT,
            phone TEXT,
            location TEXT,
            linkedin_url TEXT,
            github_url TEXT,
            portfolio_url TEXT,
            work_auth TEXT,
            sponsorship_req TEXT,
            expected_salary TEXT,
            notice_period TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs_store (
            id TEXT PRIMARY KEY,
            source TEXT,
            company TEXT,
            title TEXT,
            location TEXT,
            description TEXT,
            apply_url TEXT,
            remote_type TEXT,
            compensation TEXT,
            fetched_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_jobs(jobs: list):
    if not jobs:
        return
    conn = _connect()
    now = datetime.datetime.utcnow().isoformat()
    for j in jobs:
        conn.execute("""
            INSERT INTO jobs_store (id, source, company, title, location, description, apply_url, remote_type, compensation, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source = excluded.source,
                company = excluded.company,
                title = excluded.title,
                location = excluded.location,
                description = excluded.description,
                apply_url = excluded.apply_url,
                remote_type = excluded.remote_type,
                compensation = excluded.compensation,
                fetched_at = excluded.fetched_at
        """, (
            j.get("id"),
            j.get("source", ""),
            j.get("company", ""),
            j.get("title", ""),
            j.get("location", ""),
            j.get("description", ""),
            j.get("apply_url", ""),
            j.get("remote_type", ""),
            j.get("compensation", ""),
            now,
        ))
    conn.commit()
    conn.close()


def get_all_stored_jobs() -> list:
    conn = _connect()
    rows = conn.execute("SELECT * FROM jobs_store ORDER BY fetched_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]



def save_resume(resume_text: str, source_filename: str = ""):
    conn = _connect()
    conn.execute(
        """
        INSERT INTO resume_store (id, resume_text, source_filename, uploaded_at)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            resume_text = excluded.resume_text,
            source_filename = excluded.source_filename,
            uploaded_at = excluded.uploaded_at
        """,
        (resume_text, source_filename, datetime.datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_resume():
    conn = _connect()
    row = conn.execute("SELECT * FROM resume_store WHERE id = 1").fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def save_application(job_id: str, job: dict, status: str, resume_text: str = "",
                      cover_letter: str = "", github_repos=None):
    conn = _connect()
    conn.execute(
        """
        INSERT INTO applications
            (id, timestamp, company, title, location, compensation, status, apply_url,
             resume_text, cover_letter, github_repos)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status = excluded.status,
            resume_text = excluded.resume_text,
            cover_letter = excluded.cover_letter,
            github_repos = excluded.github_repos
        """,
        (
            job_id,
            datetime.datetime.utcnow().isoformat(),
            job.get("company", ""),
            job.get("title", ""),
            job.get("location", ""),
            job.get("compensation", "Not specified"),
            status,
            job.get("apply_url", ""),
            resume_text,
            cover_letter,
            json.dumps(github_repos or []),
        ),
    )
    conn.commit()
    conn.close()


def get_history():
    conn = _connect()
    rows = conn.execute("SELECT * FROM applications ORDER BY timestamp DESC").fetchall()
    conn.close()
    history = []
    for r in rows:
        entry = dict(r)
        try:
            entry["github_repos"] = json.loads(entry["github_repos"] or "[]")
        except (json.JSONDecodeError, TypeError):
            entry["github_repos"] = []
        history.append(entry)
    return history


def update_application_status(job_id: str, new_status: str):
    conn = _connect()
    conn.execute(
        "UPDATE applications SET status = ? WHERE id = ?",
        (new_status, job_id),
    )
    conn.commit()
    conn.close()



def get_cached_repo_analysis(repo_full_name: str, pushed_at: str):
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM repo_analysis WHERE repo_full_name = ? AND pushed_at = ?",
        (repo_full_name, pushed_at),
    ).fetchone()
    conn.close()
    return row["description"] if row else None


def save_repo_analysis(repo_full_name: str, pushed_at: str, description: str):
    conn = _connect()
    conn.execute(
        """
        INSERT INTO repo_analysis (repo_full_name, pushed_at, description)
        VALUES (?, ?, ?)
        ON CONFLICT(repo_full_name) DO UPDATE SET
            pushed_at = excluded.pushed_at,
            description = excluded.description
        """,
        (repo_full_name, pushed_at, description),
    )
    conn.commit()
    conn.close()


def save_profile(profile: dict):
    conn = _connect()
    conn.execute(
        """
        INSERT INTO profile_store (
            id, full_name, email, phone, location, linkedin_url, github_url,
            portfolio_url, work_auth, sponsorship_req, expected_salary, notice_period, updated_at
        )
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            full_name = excluded.full_name,
            email = excluded.email,
            phone = excluded.phone,
            location = excluded.location,
            linkedin_url = excluded.linkedin_url,
            github_url = excluded.github_url,
            portfolio_url = excluded.portfolio_url,
            work_auth = excluded.work_auth,
            sponsorship_req = excluded.sponsorship_req,
            expected_salary = excluded.expected_salary,
            notice_period = excluded.notice_period,
            updated_at = excluded.updated_at
        """,
        (
            profile.get("full_name", ""),
            profile.get("email", ""),
            profile.get("phone", ""),
            profile.get("location", ""),
            profile.get("linkedin_url", ""),
            profile.get("github_url", ""),
            profile.get("portfolio_url", ""),
            profile.get("work_auth", ""),
            profile.get("sponsorship_req", ""),
            profile.get("expected_salary", ""),
            profile.get("notice_period", ""),
            datetime.datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_profile() -> dict:
    conn = _connect()
    row = conn.execute("SELECT * FROM profile_store WHERE id = 1").fetchone()
    conn.close()
    if not row:
        return {
            "full_name": "",
            "email": "",
            "phone": "",
            "location": "",
            "linkedin_url": "",
            "github_url": "",
            "portfolio_url": "",
            "work_auth": "Authorized to work",
            "sponsorship_req": "No sponsorship required",
            "expected_salary": "Open / Market Rate",
            "notice_period": "Immediate",
        }
    return dict(row)