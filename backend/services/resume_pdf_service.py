import os
import subprocess
import tempfile
import shutil

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "generated_resumes")

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
    return " \\quad | \\quad ".join(parts)


def _render_entry(entry: dict) -> str:
    title = latex_escape(entry.get("title", ""))
    subtitle = latex_escape(entry.get("subtitle", ""))
    dates = latex_escape(entry.get("dates", ""))
    bullets = entry.get("bullets", []) or []

    header = ""
    if title and dates:
        header = f"\\textbf{{{title}}} \\hfill {dates} \\\\\n"
    elif title:
        header = f"\\textbf{{{title}}} \\\\\n"

    sub = f"{{\\itshape {subtitle}}} \\\\\n" if subtitle else ""

    items = ""
    if bullets:
        item_lines = "\n".join(f"\\item {latex_escape(b)}" for b in bullets)
        items = f"\\begin{{itemize}}[leftmargin=*,itemsep=1pt,topsep=2pt]\n{item_lines}\n\\end{{itemize}}\n"

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
        entry_text = "\n\\vspace{4pt}\n".join(_render_entry(e) for e in entries)
        body_parts.append(f"\\section*{{{heading}}}\n{entry_text}\n")

    body = "\n".join(body_parts)

    return f"""\\documentclass[11pt]{{article}}
\\usepackage[margin=0.75in]{{geometry}}
\\usepackage{{enumitem}}
\\usepackage{{hyperref}}
\\pagestyle{{empty}}
\\begin{{document}}
\\begin{{center}}
{{\\LARGE \\textbf{{{name}}}}} \\\\[4pt]
{contact_line}
\\end{{center}}
\\vspace{{6pt}}
{body}
\\end{{document}}
"""


def compile_resume_pdf(job_id: str, resume_data: dict) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    latex_source = render_latex(resume_data)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tex_path = os.path.join(tmp_dir, "resume.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_source)

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
            raise RuntimeError(f"LaTeX compilation failed. Log tail:\n{log_tail}")

        final_path = os.path.join(OUTPUT_DIR, f"{job_id}.pdf")
        shutil.copyfile(pdf_path, final_path)
        return final_path