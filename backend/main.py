import hashlib
import os
import csv
from fastapi import FastAPI, HTTPException, UploadFile, File, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from pypdf import PdfReader
import io

from config import settings
from services.job_sources import aggregate_jobs
from services.gemini_service import GeminiService, GeminiGenerationError
from services.github_service import fetch_github_context
from services.autofill_agent import run_ai_autofill_agent
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

JOB_CACHE: dict = {}
FAST_MATCH_CACHE: dict = {}   # heuristic scores for card list
MATCH_CACHE: dict = {}        # LLM-based detailed scores for detail view

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


class ProfileRequest(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    work_auth: str = ""
    sponsorship_req: str = ""
    expected_salary: str = ""
    notice_period: str = ""





@app.get("/jobs")
def get_jobs(keywords: str = "", location: str = "", remote_type: str = "", country: str = ""):
    jobs = aggregate_jobs(keywords=keywords, location=location, remote_type=remote_type, country=country)
    
    resume_data = storage.get_resume()
    resume_text = resume_data.get("resume_text", "") if resume_data else ""
    profile_data = storage.get_profile() or {}

    filtered_jobs = []
    kw_tokens = [k.strip().lower() for k in keywords.split() if len(k.strip()) > 2] if keywords else []

    for job in jobs:
        apply_url = job.get("apply_url") or f"{job.get('company')}:{job.get('title')}"
        job_id = hashlib.md5(apply_url.encode("utf-8")).hexdigest()[:12]
        job["id"] = job_id

        # Compute match evaluation score against candidate resume & profile facts
        match_eval = gemini.compute_fast_match_score(
            job.get("title", ""),
            job.get("description", ""),
            resume_text,
            profile_data,
        )

        job["match_score"] = match_eval.get("score", 50)
        job["match_badge"] = match_eval.get("badge", "Unrated")
        JOB_CACHE[job_id] = job
        FAST_MATCH_CACHE[job_id] = match_eval

        # Strict keyword relevance check if user searched specific terms
        if kw_tokens:
            blob = f"{job.get('title', '')} {job.get('description', '')}".lower()
            if not any(token in blob for token in kw_tokens):
                continue

        filtered_jobs.append(job)

    # Permanently store all aggregated/scraped jobs in SQLite database!
    storage.save_jobs(jobs)

    # Sort jobs by match_score descending so highest matching ML / Web Dev jobs appear FIRST!
    filtered_jobs.sort(key=lambda j: j.get("match_score", 0), reverse=True)
    return filtered_jobs




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


@app.get("/profile")
def get_user_profile():
    return storage.get_profile()


@app.post("/profile")
def save_user_profile(body: ProfileRequest):
    data = body.dict()
    storage.save_profile(data)
    return {"saved": True, "profile": data}



class StatusUpdateRequest(BaseModel):
    status: str


@app.get("/history")
def get_history():
    return storage.get_history()


@app.patch("/applications/{job_id}/status")
def update_application_status_endpoint(job_id: str, body: StatusUpdateRequest):
    storage.update_application_status(job_id, body.status)
    return {"updated": True, "job_id": job_id, "status": body.status}


@app.get("/applications/export")
def export_applications_csv():
    history = storage.get_history()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Job ID", "Timestamp", "Company", "Title", "Location", "Compensation", "Status", "Apply URL"])
    for entry in history:
        writer.writerow([
            entry.get("id", ""),
            entry.get("timestamp", ""),
            entry.get("company", ""),
            entry.get("title", ""),
            entry.get("location", ""),
            entry.get("compensation", ""),
            entry.get("status", ""),
            entry.get("apply_url", ""),
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=job_applications.csv"},
    )



AUDIT_CACHE: dict = {}


@app.get("/account/audit")
def get_portfolio_audit():
    stored = storage.get_resume()
    resume_text = stored["resume_text"] if stored else ""

    github_context = fetch_github_context(gemini)

    cache_key = f"{len(resume_text)}:{len(github_context.get('summary', ''))}"
    if cache_key in AUDIT_CACHE:
        return AUDIT_CACHE[cache_key]

    audit_result = gemini.analyze_portfolio_gaps(
        resume_text=resume_text,
        github_summary=github_context.get("summary", ""),
    )
    audit_result["github_repos"] = github_context.get("repo_names", [])
    AUDIT_CACHE[cache_key] = audit_result
    return audit_result



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


@app.get("/jobs/{job_id}/match")
def get_job_match(job_id: str):
    job = JOB_CACHE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or cache expired")

    if job_id in MATCH_CACHE:
        return MATCH_CACHE[job_id]

    resume = storage.get_resume()
    resume_text = resume["resume_text"] if resume else ""

    match_result = gemini.evaluate_job_match(
        job_title=job.get("title", ""),
        job_description=job.get("description", ""),
        resume_text=resume_text,
    )
    MATCH_CACHE[job_id] = match_result
    return match_result


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
        pdf_path = resume_pdf_service.compile_resume_pdf_from_latex(job_id, tex_source)
        used_fallback = False
    except Exception as e:
        try:
            structured = gemini.structure_resume(body.resume_text)
            pdf_path = resume_pdf_service.compile_resume_pdf_from_structured(job_id, structured)
            used_fallback = True
        except Exception as fallback_error:
            raise HTTPException(
                status_code=500,
                detail=f"PDF generation failed: {e}. Fallback error: {fallback_error}",
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

    profile = storage.get_profile()
    result = run_ai_autofill_agent(
        gemini=gemini,
        url=job["apply_url"],
        resume_text=body.resume_text,
        cover_letter=body.cover_letter,
        resume_pdf_path=body.resume_pdf_path,
        profile=profile,
    )
    return result



@app.post("/jobs/{job_id}/log")
def log_job(job_id: str, body: LogRequest):
    job = JOB_CACHE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or cache expired")

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