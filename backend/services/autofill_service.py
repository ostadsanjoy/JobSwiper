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

BLOCKED_FRAME_DOMAINS = [
    "doubleclick.net", "googletagmanager.com", "google-analytics.com",
    "googlesyndication.com", "facebook.com", "connect.facebook.net",
    "hotjar.com", "intercom.io", "drift.com", "zdassets.com", "zendesk.com",
    "hs-scripts.com", "hsforms.com", "typeform.com", "youtube.com",
    "vimeo.com", "recaptcha.net", "gstatic.com", "criteo.com",
    "bat.bing.com", "clarity.ms", "segment.com", "optimizely.com",
    "hubspot.com", "adsystem", "amazon-adsystem.com",
]


def _matches(text: str, keywords: list) -> bool:
    text = (text or "").lower()
    return any(kw in text for kw in keywords)


def _is_blocked_frame(frame) -> bool:
    url = frame.url or ""
    if not url or url == "about:blank":
        return True
    return any(domain in url for domain in BLOCKED_FRAME_DOMAINS)


def _describe_field(el, frame) -> str:
    name = el.get_attribute("name") or ""
    el_id = el.get_attribute("id") or ""
    placeholder = el.get_attribute("placeholder") or ""
    label_text = ""
    if el_id:
        label_el = frame.query_selector(f"label[for='{el_id}']")
        if label_el:
            label_text = label_el.inner_text()
    return " ".join([name, el_id, placeholder, label_text])


def _scan_frame(frame, cover_letter: str, resume_pdf_path: str):
    try:
        inputs = frame.query_selector_all("input, textarea")
    except Exception:
        return []

    candidates = []
    for el in inputs:
        try:
            context = _describe_field(el, frame)
            input_type = (el.get_attribute("type") or "text").lower()

            if input_type == "hidden":
                continue
            if input_type == "file":
                if _matches(context, FIELD_KEYWORDS["resume_file"]):
                    candidates.append(("resume_file", el, context))
                else:
                    candidates.append(("file_other", el, context))
                continue
            if _matches(context, FIELD_KEYWORDS["email"]):
                candidates.append(("email", el, context))
            elif _matches(context, FIELD_KEYWORDS["phone"]):
                candidates.append(("phone", el, context))
            elif _matches(context, FIELD_KEYWORDS["cover_letter"]):
                candidates.append(("cover_letter", el, context))
            elif _matches(context, FIELD_KEYWORDS["first_name"] + FIELD_KEYWORDS["last_name"] + FIELD_KEYWORDS["full_name"]):
                candidates.append(("name", el, context))
        except Exception:
            continue

    return candidates


def _apply_candidates(candidates, frame, cover_letter: str, resume_pdf_path: str):
    filled = []
    unfilled = []
    frame_label = frame.url[:60] if frame.url else "unknown frame"

    for kind, el, context in candidates:
        try:
            if kind == "resume_file":
                if resume_pdf_path:
                    el.set_input_files(resume_pdf_path)
                    filled.append(f"resume file upload <- generated PDF resume [{frame_label}]")
                else:
                    unfilled.append(f"file upload field ({context.strip() or 'unlabeled'}) [{frame_label}] - attach manually")
            elif kind == "file_other":
                unfilled.append(f"file upload field ({context.strip() or 'unlabeled'}) [{frame_label}] - attach manually")
            elif kind == "email":
                el.fill("your.email@example.com")
                filled.append(f"email <- placeholder (edit before submit) [{frame_label}]")
            elif kind == "phone":
                el.fill("000-000-0000")
                filled.append(f"phone <- placeholder (edit before submit) [{frame_label}]")
            elif kind == "cover_letter":
                el.fill(cover_letter)
                filled.append(f"cover letter field <- tailored cover letter [{frame_label}]")
            elif kind == "name":
                unfilled.append(f"name field ({context.strip() or 'unlabeled'}) [{frame_label}] - fill manually, not guessed")
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
    frames_considered = 0
    frames_skipped_as_thirdparty = 0

    for frame in page.frames:
        if _is_blocked_frame(frame):
            frames_skipped_as_thirdparty += 1
            continue
        frames_considered += 1

        candidates = _scan_frame(frame, cover_letter, resume_pdf_path)
        distinct_kinds = {kind for kind, _, _ in candidates}
        has_file_signal = "resume_file" in distinct_kinds or "file_other" in distinct_kinds

        if len(distinct_kinds) < 2 and not has_file_signal:
            continue

        filled, unfilled = _apply_candidates(candidates, frame, cover_letter, resume_pdf_path)
        all_filled.extend(filled)
        all_unfilled.extend(unfilled)

    return {
        "resume_pdf_used": bool(resume_pdf_path),
        "resume_txt_fallback": fallback_txt_path,
        "filled_fields": all_filled,
        "needs_manual_attention": all_unfilled,
        "frames_scanned": len(page.frames),
        "frames_considered": frames_considered,
        "frames_skipped_as_thirdparty": frames_skipped_as_thirdparty,
        "note": "Browser window left open. Review all filled fields, then submit yourself.",
    }