import tempfile
import os
from playwright.sync_api import sync_playwright

BLOCKED_FRAME_DOMAINS = [
    "doubleclick.net", "googletagmanager.com", "google-analytics.com",
    "googlesyndication.com", "facebook.com", "connect.facebook.net",
    "hotjar.com", "intercom.io", "drift.com", "typeform.com", "recaptcha.net",
    "criteo.com", "clarity.ms", "segment.com", "optimizely.com",
]

APPLY_BUTTON_KEYWORDS = ["apply for this job", "apply now", "apply", "submit application"]


def _is_blocked_frame(frame) -> bool:
    url = frame.url or ""
    if not url or url == "about:blank":
        return True
    return any(domain in url for domain in BLOCKED_FRAME_DOMAINS)


def _get_field_label(el, frame) -> str:
    name = el.get_attribute("name") or ""
    el_id = el.get_attribute("id") or ""
    placeholder = el.get_attribute("placeholder") or ""
    aria_label = el.get_attribute("aria-label") or ""

    label_text = ""
    if el_id:
        try:
            label_el = frame.query_selector(f"label[for='{el_id}']")
            if label_el:
                label_text = label_el.inner_text()
        except Exception:
            pass

    if not label_text and name:
        try:
            parent = el.evaluate_handle("el => el.closest('label')")
            if parent:
                label_text = parent.inner_text()
        except Exception:
            pass

    parts = [p.strip() for p in [label_text, aria_label, placeholder, name, el_id] if p and p.strip()]
    return " / ".join(parts) or "Unlabeled field"


def run_ai_autofill_agent(
    gemini, url: str, resume_text: str, cover_letter: str, resume_pdf_path: str = "", profile: dict = None
) -> dict:
    fallback_txt_path = os.path.join(tempfile.gettempdir(), "tailored_resume.txt")
    with open(fallback_txt_path, "w", encoding="utf-8") as f:
        f.write(resume_text)

    p = sync_playwright().start()
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(url, timeout=30000)

    try:
        page.wait_for_load_state("networkidle", timeout=6000)
    except Exception:
        pass

    # Try clicking "Apply" button if landing page has one before form
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

    for frame in page.frames:
        if _is_blocked_frame(frame):
            continue
        frames_considered += 1

        try:
            elements = frame.query_selector_all("input, textarea, select")
        except Exception:
            continue

        field_descriptors = []
        element_map = {}

        for idx, el in enumerate(elements):
            try:
                input_type = (el.get_attribute("type") or "text").lower()
                if input_type == "hidden":
                    continue

                field_id = f"field_{idx}"
                label = _get_field_label(el, frame)

                options = []
                tag_name = el.evaluate("el => el.tagName.toLowerCase()")
                if tag_name == "select":
                    try:
                        opts = el.query_selector_all("option")
                        options = [o.inner_text().strip() for o in opts if o.inner_text().strip()]
                    except Exception:
                        pass

                field_descriptors.append({
                    "field_id": field_id,
                    "tag": tag_name,
                    "type": input_type,
                    "label": label,
                    "options": options[:15],
                })
                element_map[field_id] = (el, tag_name, input_type, label)
            except Exception:
                continue

        if not field_descriptors:
            continue

        # Call Gemini AI Agent to decide actions for all detected fields
        try:
            ai_response = gemini.map_application_fields(
                fields=field_descriptors,
                resume_text=resume_text,
                cover_letter=cover_letter,
                profile=profile,
            )
            actions = ai_response.get("actions", {})
        except Exception as e:
            actions = {}

        # Execute AI actions with Playwright
        for field_id, (el, tag, input_type, label) in element_map.items():
            action_info = actions.get(field_id, {})
            action = action_info.get("action", "skip")
            val = action_info.get("value", "")

            try:
                if action == "upload_resume" or input_type == "file":
                    if resume_pdf_path and os.path.exists(resume_pdf_path):
                        el.set_input_files(resume_pdf_path)
                        all_filled.append(f"PDF Resume attached -> {label}")
                    else:
                        all_unfilled.append(f"File upload needed -> {label}")
                elif action == "fill" and val:
                    el.fill(str(val))
                    all_filled.append(f"AI filled '{val[:30]}...' -> {label}")
                elif action == "select" and val:
                    try:
                        el.select_option(label=val)
                    except Exception:
                        el.select_option(value=val)
                    all_filled.append(f"AI selected '{val}' -> {label}")
                elif action == "check":
                    if str(val).lower() == "true":
                        el.check()
                    all_filled.append(f"AI checked -> {label}")
                else:
                    all_unfilled.append(f"Manual attention -> {label}")
            except Exception as fill_err:
                all_unfilled.append(f"Could not fill -> {label} ({fill_err})")

    return {
        "resume_pdf_used": bool(resume_pdf_path),
        "filled_fields": all_filled,
        "needs_manual_attention": all_unfilled,
        "frames_scanned": len(page.frames),
        "frames_considered": frames_considered,
        "note": "AI Agent filled fields. Review the browser window before submitting.",
    }
