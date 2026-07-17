import tempfile
import os
from playwright.sync_api import sync_playwright

FIELD_KEYWORDS = {
    "first_name": ["first name", "firstname", "fname"],
    "last_name": ["last name", "lastname", "lname"],
    "full_name": ["full name", "your name"],
    "email": ["email"],
    "phone": ["phone", "mobile"],
    "linkedin": ["linkedin"],
    "website": ["portfolio", "website", "personal site"],
    "cover_letter": ["cover letter", "why do you want", "additional information"],
    "resume_file": ["resume", "cv"],
}

APPLY_BUTTON_KEYWORDS = ["apply for this job", "apply now", "apply"]


def _matches(text: str, keywords: list) -> bool:
    text = (text or "").lower()
    return any(kw in text for kw in keywords)


def _fill_frame(frame, cover_letter: str, resume_pdf_path: str) -> tuple:
    filled = []
    unfilled = []

    try:
        inputs = frame.query_selector_all("input, textarea")
    except Exception:
        return filled, unfilled

    for el in inputs:
        try:
            name = el.get_attribute("name") or ""
            el_id = el.get_attribute("id") or ""
            placeholder = el.get_attribute("placeholder") or ""
            label_text = ""
            if el_id:
                label_el = frame.query_selector(f"label[for='{el_id}']")
                if label_el:
                    label_text = label_el.inner_text()

            context = " ".join([name, el_id, placeholder, label_text])
            input_type = (el.get_attribute("type") or "text").lower()

            if input_type == "file":
                if resume_pdf_path and _matches(context, FIELD_KEYWORDS["resume_file"]):
                    el.set_input_files(resume_pdf_path)
                    filled.append("resume file upload <- generated PDF resume")
                else:
                    unfilled.append(f"file upload field ({context.strip() or 'unlabeled'}) - attach manually")
                continue
            if input_type == "hidden":
                continue

            if _matches(context, FIELD_KEYWORDS["email"]):
                el.fill("your.email@example.com")
                filled.append("email <- placeholder (edit before submit)")
            elif _matches(context, FIELD_KEYWORDS["phone"]):
                el.fill("000-000-0000")
                filled.append("phone <- placeholder (edit before submit)")
            elif _matches(context, FIELD_KEYWORDS["cover_letter"]):
                el.fill(cover_letter)
                filled.append("cover letter field <- tailored cover letter")
            elif _matches(context, FIELD_KEYWORDS["first_name"] + FIELD_KEYWORDS["last_name"] + FIELD_KEYWORDS["full_name"]):
                unfilled.append(f"name field ({context.strip() or 'unlabeled'}) - fill manually, not guessed to avoid errors")
            else:
                pass
        except Exception:
            continue

    return filled, unfilled


def autofill_application(url: str, resume_text: str, cover_letter: str, resume_pdf_path: str = "") -> dict:
    fallback_txt_path = os.path.join(tempfile.gettempdir(), "tailored_resume.txt")
    with open(fallback_txt_path, "w") as f:
        f.write(resume_text)

    p = sync_playwright().start()
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(url, timeout=30000)

    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass

    try:
        for kw in APPLY_BUTTON_KEYWORDS:
            btn = page.get_by_role("link", name=kw, exact=False).first
            if btn.count() > 0:
                btn.click(timeout=3000)
                page.wait_for_timeout(1500)
                break
    except Exception:
        pass

    page.wait_for_timeout(1500)

    all_filled = []
    all_unfilled = []
    for frame in page.frames:
        filled, unfilled = _fill_frame(frame, cover_letter, resume_pdf_path)
        all_filled.extend(filled)
        all_unfilled.extend(unfilled)

    return {
        "resume_pdf_used": bool(resume_pdf_path),
        "resume_txt_fallback": fallback_txt_path,
        "filled_fields": all_filled,
        "needs_manual_attention": all_unfilled,
        "frames_scanned": len(page.frames),
        "note": "Browser window left open. Review all filled fields, then submit yourself.",
    }