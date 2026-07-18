import uuid
import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pypdf import PdfReader
import io

from config import settings
from services.job_sources import aggregate_jobs
from services.gemini_service import GeminiService, GeminiGenerationError
from services.github_service import fetch_github_context
from services.sheets_service import SheetsService
from services.autofill_service import autofill_application
from services import storage
from services import resume_pdf_service

storage.init_db()

app = FastAPI(title="Job Swiper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

gemini = GeminiService()
sheets = SheetsService()

JOB_CACHE: dict = {}

GENERATED_RESUMES_DIR = os.path.join(os.path.dirname(__file__), "generated_resumes")


class TailorRequest(BaseModel):
    base_resume: str = ""


class ResumePdfRequest(BaseModel):
    resume_text: str


class AutofillRequest(BaseModel):
    resume_text: str
    cover_letter: str
    resume_pdf_path: str = ""


class LogRequest(BaseModel):
    status: str
    resume_text: str = ""
    cover_letter: str = ""
    github_repos: list = []


@app.get("/jobs")
def get_jobs(keywords: str = "", location: str = "", remote_type: str = "", country: str = ""):
    jobs = aggregate_jobs(keywords=keywords, location=location, remote_type=remote_type, country=country)
    for job in jobs:
        job_id = str(uuid.uuid4())
        job["id"] = job_id
        JOB_CACHE[job_id] = job
    return jobs


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = JOB_CACHE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or cache expired")
    return job


@app.post("/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported right now.")

    raw = await file.read()
    try:
        reader = PdfReader(io.BytesIO(raw))
        text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read that PDF: {e}")

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Extracted no text from that PDF - it may be a scanned image rather than real text.",
        )

    storage.save_resume(text, source_filename=file.filename)
    return {"resume_text": text, "filename": file.filename}


@app.get("/resume/current")
def get_current_resume():
    resume = storage.get_resume()
    if not resume:
        return {"resume_text": "", "source_filename": "", "uploaded_at": None}
    return resume


@app.get("/history")
def get_history():
    return storage.get_history()


@app.post("/jobs/{job_id}/tailor")
def tailor_job(job_id: str, body: TailorRequest):
    job = JOB_CACHE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or cache expired")

    base_resume = body.base_resume
    if not base_resume:
        stored = storage.get_resume()
        base_resume = stored["resume_text"] if stored else ""
    if not base_resume:
        raise HTTPException(status_code=400, detail="No resume on file - upload a PDF resume first.")

    github_context = fetch_github_context(gemini)
    try:
        tailored_resume = gemini.tailor_resume(
            base_resume=base_resume,
            job_description=job["description"],
            github_summary=github_context["summary"],
        )
        cover_letter = gemini.generate_cover_letter(
            job=job,
            base_resume=base_resume,
            github_summary=github_context["summary"],
        )
    except GeminiGenerationError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "resume": tailored_resume,
        "cover_letter": cover_letter,
        "github_repos": github_context["repo_names"],
    }


@app.post("/jobs/{job_id}/resume-pdf")
def generate_resume_pdf(job_id: str, body: ResumePdfRequest):
    job = JOB_CACHE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or cache expired")

    github_context = fetch_github_context(gemini)

    try:
        tex_source = gemini.generate_resume_latex(
            base_resume=body.resume_text,
            job_description=job["description"],
            github_summary=github_context["summary"],
        )
    except GeminiGenerationError as e:
        raise HTTPException(status_code=502, detail=str(e))

    pdf_path = None
    used_fallback = False
    last_error = None

    for attempt in range(2):
        try:
            pdf_path = resume_pdf_service.compile_resume_pdf_from_latex(job_id, tex_source)
            break
        except RuntimeError as e:
            last_error = str(e)
            if attempt == 0:
                try:
                    tex_source = gemini.generate_resume_latex(
                        base_resume=body.resume_text,
                        job_description=job["description"],
                        github_summary=github_context["summary"],
                        previous_latex=tex_source,
                        error_log=last_error,
                    )
                except GeminiGenerationError:
                    break

    if not pdf_path:
        try:
            structured = gemini.structure_resume(body.resume_text)
            pdf_path = resume_pdf_service.compile_resume_pdf_from_structured(job_id, structured)
            used_fallback = True
        except (GeminiGenerationError, RuntimeError) as e:
            raise HTTPException(
                status_code=500,
                detail=f"PDF generation failed after retries and fallback: {e}. Last LaTeX error: {last_error}",
            )

    return {"pdf_path": pdf_path, "used_fallback_template": used_fallback}


@app.get("/jobs/{job_id}/resume-pdf/file")
def get_resume_pdf_file(job_id: str):
    path = os.path.join(GENERATED_RESUMES_DIR, f"{job_id}.pdf")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="No generated PDF for this job yet.")
    return FileResponse(path, media_type="application/pdf", filename=f"resume_{job_id}.pdf")


@app.post("/jobs/{job_id}/autofill")
def autofill_job(job_id: str, body: AutofillRequest):
    job = JOB_CACHE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or cache expired")

    result = autofill_application(
        url=job["apply_url"],
        resume_text=body.resume_text,
        cover_letter=body.cover_letter,
        resume_pdf_path=body.resume_pdf_path,
    )
    return result


@app.post("/jobs/{job_id}/log")
def log_job(job_id: str, body: LogRequest):
    job = JOB_CACHE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or cache expired")

    sheets.log_application(job=job, status=body.status)
    storage.save_application(
        job_id=job_id,
        job=job,
        status=body.status,
        resume_text=body.resume_text,
        cover_letter=body.cover_letter,
        github_repos=body.github_repos,
    )
    return {"logged": True}


@app.get("/health")
def health():
    return {"status": "ok", "model_primary": settings.gemini_model_primary}