# Job Swiper

A personal job-search tool: swipeable job cards sourced from Greenhouse, Lever, Adzuna, and Arbeitnow, with Gemini-tailored resumes/cover letters, LaTeX-generated PDF resumes, and semi-automated form filling. Autofill stops short of clicking submit - you review and send each application yourself.

## Architecture

```
job-swiper/
├── backend/               FastAPI app
│   ├── main.py             API routes
│   ├── config.py           env-driven settings
│   ├── services/
│   │   ├── job_sources.py    Greenhouse/Lever/Adzuna/Arbeitnow aggregation
│   │   ├── gemini_service.py Gemini calls: tailoring, cover letters, repo analysis, resume structuring
│   │   ├── github_service.py GitHub repo fetch + Gemini-based code analysis, with caching
│   │   ├── resume_pdf_service.py structured resume JSON -> LaTeX -> compiled PDF
│   │   ├── autofill_service.py Playwright form filling + PDF auto-attach
│   │   ├── sheets_service.py Google Sheets logging
│   │   └── storage.py        local SQLite: resume, application history, repo-analysis cache
│   ├── job_swiper.db       SQLite file, created on first run (gitignored)
│   └── generated_resumes/  compiled PDFs, one per job id (gitignored)
└── frontend/               React + Vite
    └── src/
        ├── App.jsx           top-level state machine and tab switching
        ├── api.js             backend client
        └── components/
            ├── SearchBar.jsx
            ├── JobCard.jsx
            ├── JobDetailModal.jsx
            ├── ReviewModal.jsx
            ├── ResumeUpload.jsx
            └── AccountPage.jsx
```

## Prerequisites

- Python 3.10+
- Node 18+
- A LaTeX distribution with `pdflatex` on your PATH. On Windows, install MiKTeX (auto-installs missing packages on first compile). On macOS, MacTeX. On Linux, texlive-latex-recommended and texlive-latex-extra via your package manager.
- A Gemini API key
- A GitHub personal access token (fine-grained, read-only, public repos or select repos)
- A Google Cloud service account for Sheets logging (optional - the app still runs and stores history in SQLite without it)
- An Adzuna developer account (optional - Greenhouse/Lever/Arbeitnow still work without it)

## Setup

```bash
cd backend
python3 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env        # then fill in your keys
uvicorn main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```


## Environment variables

See backend/.env.example for the full list. **Key ones:** `GEMINI_API_KEY, GEMINI_MODEL_PRIMARY, GEMINI_MODEL_FALLBACK, GITHUB_TOKEN, GITHUB_USERNAME, GOOGLE_SHEETS_CREDS_FILE, GOOGLE_SHEET_NAME, GREENHOUSE_BOARD_TOKENS, LEVER_COMPANIES, ADZUNA_APP_ID, ADZUNA_APP_KEY, ADZUNA_COUNTRIES.`

## What "autofill" actually does

It opens the job posting in a visible Chromium window, matches form fields by name/id/placeholder/label text across every frame on the page (including embedded application iframes), fills email/phone/cover-letter text fields, and attaches the generated PDF resume to any file-upload field it recognizes as a resume field. It does not click submit. You review the filled-out form and submit it yourself.

## Known limitations

- Field-matching heuristics are tuned mainly against Greenhouse-style forms. Workday and heavily custom portals will need more manual attention.
- Compensation data is structured (reliable) from Adzuna, and best-effort regex extraction from everything else - treat "Not specified" as "we couldn't find one," not "there is none."
- Repo analysis calls Gemini once per repo and caches by pushed_at, so re-running against unchanged repos is cheap after the first pass.