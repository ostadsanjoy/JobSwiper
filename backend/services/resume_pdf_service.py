import os
import subprocess
import tempfile
import requests

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "generated_resumes")

CLOUD_COMPILE_URL = "https://latex.ytotech.com/builds/sync"

LATEX_ESCAPE_MAP = {
    "\\": "\\textbackslash{}",
    "&": "\\&",
    "%": "\\%",
    "$": "\\$",
    "#": "\\#",
    "_": "\\_",
    "{": "\\{",
    "}": "\\}",
    "~": "\\textasciitilde{}",
    "^": "\\textasciicircum{}",
}


def latex_escape(text) -> str:
    if not text:
        return ""
    return "".join(LATEX_ESCAPE_MAP.get(ch, ch) for ch in str(text))


def _render_contact_line(contact: dict) -> str:
    parts = []
    for key in ("email", "phone", "location", "linkedin", "github"):
        value = contact.get(key)
        if value:
            parts.append(latex_escape(value))
    return " \\quad $\\vert$ \\quad ".join(parts)


def _render_entry(entry: dict) -> str:
    title = latex_escape(entry.get("title", ""))
    subtitle = latex_escape(entry.get("subtitle", ""))
    dates = latex_escape(entry.get("dates", ""))
    bullets = entry.get("bullets", []) or []

    header = ""
    if title and dates:
        header = f"\\textbf{{{title}}} \\hfill \\textit{{{dates}}} \\\\\n"
    elif title:
        header = f"\\textbf{{{title}}} \\\\\n"

    sub = f"{{\\small\\itshape {subtitle}}} \\\\\n" if subtitle else ""

    items = ""
    if bullets:
        item_lines = "\n".join(f"\\item {latex_escape(b)}" for b in bullets)
        items = f"\\begin{{itemize}}[leftmargin=14pt,itemsep=0pt,topsep=2pt,parsep=0pt]\n{item_lines}\n\\end{{itemize}}\n"

    return header + sub + items


def render_latex(resume_data: dict) -> str:
    name = latex_escape(resume_data.get("name", ""))
    contact_line = _render_contact_line(resume_data.get("contact", {}) or {})
    summary = latex_escape(resume_data.get("summary", ""))
    sections = resume_data.get("sections", []) or []

    body_parts = []
    if summary:
        body_parts.append(f"\\section*{{Summary}}\n{summary}\n")

    for section in sections:
        heading = latex_escape(section.get("heading", ""))
        entries = section.get("entries", []) or []
        entry_text = "\n\\vspace{3pt}\n".join(_render_entry(e) for e in entries)
        body_parts.append(f"\\section*{{{heading}}}\n{entry_text}\n")

    body = "\n\\vspace{2pt}\n".join(body_parts)

    return f"""\\documentclass[10.5pt]{{article}}
\\usepackage[margin=0.55in]{{geometry}}
\\usepackage{{enumitem}}
\\usepackage{{hyperref}}
\\usepackage{{titlesec}}
\\usepackage{{lmodern}}
\\titleformat{{\\section}}{{\\large\\bfseries}}{{}}{{0em}}{{}}[\\titlerule]
\\titlespacing{{\\section}}{{0pt}}{{7pt}}{{4pt}}
\\pagestyle{{empty}}
\\setlength{{\\parindent}}{{0pt}}
\\begin{{document}}
\\begin{{center}}
{{\\LARGE \\textbf{{{name}}}}} \\\\[3pt]
{{\\small {contact_line}}}
\\end{{center}}
{body}
\\end{{document}}
"""


def _compile_via_cloud(tex_source: str) -> bytes:
    resp = requests.post(
        CLOUD_COMPILE_URL,
        json={"compiler": "pdflatex", "resources": [{"main": True, "content": tex_source}]},
        timeout=40,
    )
    content_type = resp.headers.get("Content-Type", "")
    if resp.status_code not in (200, 201) or "pdf" not in content_type:
        raise RuntimeError(f"Cloud LaTeX service returned {resp.status_code}: {resp.text[:800]}")
    return resp.content


def _compile_via_local(tex_source: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tex_path = os.path.join(tmp_dir, "resume.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_source)

        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
             "-output-directory", tmp_dir, tex_path],
            capture_output=True,
            text=True,
            timeout=60,
        )

        pdf_path = os.path.join(tmp_dir, "resume.pdf")
        if result.returncode != 0 or not os.path.exists(pdf_path):
            log_tail = (result.stdout or "")[-1500:]
            raise RuntimeError(f"Local pdflatex failed: {log_tail}")

        with open(pdf_path, "rb") as f:
            return f.read()


def compile_latex_to_pdf_bytes(tex_source: str) -> bytes:
    try:
        return _compile_via_cloud(tex_source)
    except Exception as cloud_error:
        try:
            return _compile_via_local(tex_source)
        except FileNotFoundError:
            raise RuntimeError(
                f"Cloud compile failed ({cloud_error}) and no local pdflatex is installed as a fallback."
            )
        except Exception as local_error:
            raise RuntimeError(f"Cloud compile failed: {cloud_error}. Local compile also failed: {local_error}")


def save_pdf_bytes(job_id: str, pdf_bytes: bytes) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    final_path = os.path.join(OUTPUT_DIR, f"{job_id}.pdf")
    with open(final_path, "wb") as f:
        f.write(pdf_bytes)
    return final_path


def compile_resume_pdf_from_latex(job_id: str, tex_source: str) -> str:
    pdf_bytes = compile_latex_to_pdf_bytes(tex_source)
    return save_pdf_bytes(job_id, pdf_bytes)


def compile_resume_pdf_from_structured(job_id: str, resume_data: dict) -> str:
    tex_source = render_latex(resume_data)
    pdf_bytes = compile_latex_to_pdf_bytes(tex_source)
    return save_pdf_bytes(job_id, pdf_bytes)