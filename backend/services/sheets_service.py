import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import settings

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

HEADER_ROW = ["timestamp", "company", "title", "location", "compensation", "status", "apply_url"]


class SheetsService:
    """
    Logs every swipe (applied or skipped) to a Google Sheet.
    Setup: create a Google Cloud service account, enable Sheets + Drive API,
    download the JSON key as credentials.json, then share your target sheet
    with the service account's email address (found inside that JSON).
    """

    def __init__(self):
        self._sheet = None

    def _get_sheet(self):
        if self._sheet is not None:
            return self._sheet
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                settings.google_sheets_creds_file, SCOPE
            )
            client = gspread.authorize(creds)
            spreadsheet = client.open(settings.google_sheet_name)
            self._sheet = spreadsheet.sheet1
            existing = self._sheet.row_values(1)
            if not existing:
                self._sheet.append_row(HEADER_ROW)
            elif existing != HEADER_ROW:
                # Older sheet from before the compensation column existed -
                # leave existing rows alone, just note it in the console
                # rather than silently misaligning columns.
                print(
                    "[sheets_service] header row doesn't match expected columns "
                    f"{HEADER_ROW} - got {existing}. New rows will still append "
                    "in the new column order; consider updating row 1 manually."
                )
        except Exception as e:
            print(f"[sheets_service] could not connect to Google Sheets: {e}")
            self._sheet = None
        return self._sheet

    def log_application(self, job: dict, status: str):
        sheet = self._get_sheet()
        if sheet is None:
            print(f"[sheets_service] skipped logging (no sheet connection): {job.get('title')}")
            return
        sheet.append_row([
            datetime.datetime.utcnow().isoformat(),
            job.get("company", ""),
            job.get("title", ""),
            job.get("location", ""),
            job.get("compensation", "Not specified"),
            status,
            job.get("apply_url", ""),
        ])