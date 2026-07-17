import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model_primary: str = os.getenv("GEMINI_MODEL_PRIMARY", "gemini-3.1-flash-lite")
    gemini_model_fallback: str = os.getenv("GEMINI_MODEL_FALLBACK", "gemini-2.5-flash")

    github_token: str = os.getenv("GITHUB_TOKEN", "")
    github_username: str = os.getenv("GITHUB_USERNAME", "")

    google_sheets_creds_file: str = os.getenv("GOOGLE_SHEETS_CREDS_FILE", "credentials.json")
    google_sheet_name: str = os.getenv("GOOGLE_SHEET_NAME", "JobApplications")

    greenhouse_board_tokens: list = [
        t.strip() for t in os.getenv("GREENHOUSE_BOARD_TOKENS", "").split(",") if t.strip()
    ]
    lever_companies: list = [
        c.strip() for c in os.getenv("LEVER_COMPANIES", "").split(",") if c.strip()
    ]

    adzuna_app_id: str = os.getenv("ADZUNA_APP_ID", "")
    adzuna_app_key: str = os.getenv("ADZUNA_APP_KEY", "")
    adzuna_countries: list = [
        c.strip() for c in os.getenv("ADZUNA_COUNTRIES", "us,in").split(",") if c.strip()
    ]


settings = Settings()