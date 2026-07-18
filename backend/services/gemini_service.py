import json
import re
import google.generativeai as genai
from config import settings

genai.configure(api_key=settings.gemini_api_key)


class GeminiGenerationError(Exception):
    pass


class GeminiService:
    def __init__(self):
        self.primary_model = genai.GenerativeModel(settings.gemini_model_primary)
        self.fallback_model = genai.GenerativeModel(settings.gemini_model_fallback)

    def _generate(self, prompt: str) -> str:
        primary_error = None
        try:
            response = self.primary_model.generate_content(prompt)
            text = (response.text or "").strip()
            if text:
                return text
            primary_error = "primary model returned an empty response"
        except Exception as e:
            primary_error = str(e)

        try:
            response = self.fallback_model.generate_content(prompt)
            text = (response.text or "").strip()
            if text:
                return text
            raise GeminiGenerationError(
                f"Both models failed. Primary: {primary_error}. Fallback: returned an empty response."
            )
        except GeminiGenerationError:
            raise
        except Exception as e:
            raise GeminiGenerationError(f"Both models failed. Primary: {primary_error}. Fallback: {e}")

    def _generate_json(self, prompt: str) -> dict:
        raw = self._generate(prompt)
        cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise GeminiGenerationError(f"Model did not return valid JSON: {e}. Raw: {raw[:300]}")

    def _clean_latex(self, raw: str) -> str:
        cleaned = re.sub(r"^```(latex|tex)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        return cleaned

    BULLET_RULES = """Each project/experience entry must have 2-4 bullet points following
these rules strictly:
- Start with a strong action verb and name the specific tools/technologies
  used (e.g. "Built REST APIs using Java and Spring Boot" not "Worked on
  backend APIs").
- Include a quantifiable outcome wherever the source material supports one -
  percentage improvements, scale (users/records/requests), time saved, or
  similar. Never fabricate a number that isn't grounded in the source.
- Naturally mirror relevant terminology from the job description where it
  truthfully applies, to help ATS keyword matching - do not force irrelevant
  keywords in.
- Keep each bullet a single concise line - challenge/role/result, not a
  paragraph."""

    def tailor_resume(self, base_resume: str, job_description: str, github_summary: str) -> str:
        prompt = f"""You are an expert ATS resume writer and technical recruiter. Rewrite
the resume below into an ATS-optimized version tailored specifically to the
target job description.

RULES:
- Preserve factual accuracy. Do NOT invent experience, employers, projects,
  metrics, or skills not supported by the base resume or GitHub summary.
{self.BULLET_RULES}
- Use the GitHub summary to build or strengthen a Projects section with
  real project names and the actual technical descriptions provided - do
  not paraphrase into vague generic language.
- Structure the output with clear section headers, in this order, omitting
  any section with no real content: SUMMARY, PROFESSIONAL EXPERIENCE,
  SKILLS, PROJECTS, EDUCATION, CERTIFICATIONS, ACHIEVEMENTS.
- Keep it concise enough to fit one page for a candidate at this
  experience level - prioritize the most relevant bullets over completeness.

BASE RESUME:
{base_resume}

GITHUB PROJECT SUMMARY (real project names and Gemini-analyzed descriptions
of what each project's code actually does - use these directly for the
Projects section, do not invent different ones):
{github_summary}

TARGET JOB DESCRIPTION:
{job_description}

Output only the tailored resume text with section headers, no commentary."""
        return self._generate(prompt)

    def generate_cover_letter(self, job: dict, base_resume: str, github_summary: str) -> str:
        prompt = f"""Write a concise, specific cover letter (under 300 words) for the
role below. Reference 1-2 real, relevant details from the candidate's resume
or GitHub projects. Avoid generic filler phrases. Do not invent facts.

ROLE: {job.get('title', '')} at {job.get('company', '')}

JOB DESCRIPTION:
{job.get('description', '')}

CANDIDATE RESUME:
{base_resume}

CANDIDATE GITHUB SUMMARY:
{github_summary}

Output only the cover letter text, no commentary."""
        return self._generate(prompt)

    def analyze_repo(self, repo_name: str, readme_text: str, file_names: list) -> str:
        prompt = f"""Look at this GitHub repository's actual contents below and write a
2-3 sentence technical description of what the code does. Be specific about
functionality, the tech stack, and any notable implementation details you can
infer from the README and file list. Do not write generic boilerplate like
"a well-structured project" - describe what it actually does and how.

REPO NAME: {repo_name}

TOP-LEVEL FILES: {", ".join(file_names) if file_names else "none listed"}

README CONTENT:
{readme_text[:4000] if readme_text else "No README found."}

Output only the 2-3 sentence description, no commentary, no markdown."""
        return self._generate(prompt)

    def structure_resume(self, tailored_resume_text: str) -> dict:
        prompt = f"""Convert the resume text below into strict JSON matching this
exact schema, with no markdown fences and no commentary - just the JSON:

{{
  "name": "string",
  "contact": {{"email": "string", "phone": "string", "linkedin": "string", "github": "string", "location": "string"}},
  "summary": "string",
  "sections": [
    {{
      "heading": "string",
      "entries": [
        {{"title": "string", "subtitle": "string", "dates": "string", "bullets": ["string", "string"]}}
      ]
    }}
  ]
}}

Section order must be, omitting any with no real content: Professional
Experience, Skills, Projects, Education, Certifications, Achievements. Use
empty strings for any contact fields not present in the source resume. For
a Skills section, put the skill list as a single bullet in one entry with
empty title/subtitle/dates. Preserve all real content and every bullet from
the source resume exactly - do not drop bullets, do not invent new ones.
Keep total content tight enough to render as one page.

SOURCE RESUME:
{tailored_resume_text}"""
        return self._generate_json(prompt)

    def generate_resume_latex(self, base_resume: str, job_description: str, github_summary: str,
                               previous_latex: str = "", error_log: str = "") -> str:
        if previous_latex and error_log:
            prompt = f"""The LaTeX document below failed to compile with pdflatex. Fix ONLY
what is causing the compile error shown in the log - keep every other part
of the content and structure identical. Output ONLY the complete corrected
LaTeX code, no commentary, no markdown fences.

PREVIOUS LATEX:
{previous_latex}

COMPILE ERROR LOG:
{error_log}

Output only the corrected complete LaTeX document."""
            return self._clean_latex(self._generate(prompt))

        prompt = f"""You are an expert ATS resume writer and LaTeX resume designer.
Produce a COMPLETE, Overleaf-compatible LaTeX document for a one-page,
ATS-optimized, professional software engineering resume tailored to the
target job description below.

CONTENT RULES:
- Preserve factual accuracy. Do NOT invent experience, employers, projects,
  metrics, or skills not supported by the base resume or GitHub summary.
{self.BULLET_RULES}
- Use the GitHub summary to populate a Projects section with real project
  names and the actual technical descriptions provided.
- Extract key terminology from the job description and naturally integrate
  truthful, matching keywords - do not keyword-stuff.
- Section order, omitting any with no real content: Header, Summary,
  Professional Experience, Projects, Technical Skills, Education,
  Certifications, Achievements.

LATEX TECHNICAL RULES:
- Use ONLY these packages, all standard and pre-installed on any TeX
  distribution: geometry, enumitem, titlesec, hyperref. Do not use
  fontawesome, moderncv, or any icon/font package that might not be
  installed - use plain text separators instead of icons.
- documentclass[10.5pt]{{article}}, margins around 0.55in via geometry.
- Correctly escape every LaTeX special character in body text: \\ & % $ # _
  {{ }} ~ ^ must all be properly escaped so the document compiles cleanly.
- Header: name large and bold, centered; contact line (email, phone,
  location, LinkedIn, GitHub - whichever exist) centered below it in a
  smaller font, separated by " | ".
- Section headings should use \\section* with a titlerule underneath via
  titlesec, consistent spacing, no page numbers (\\pagestyle{{empty}}).
- Each project/experience entry: bold title with the date range right-
  aligned via \\hfill on the same line, an italic subtitle line for the
  tech stack if relevant, then a tight itemize block for bullets
  (leftmargin=14pt, itemsep=0pt, topsep=2pt, parsep=0pt).
- The document MUST compile standalone with pdflatex with no missing
  references or undefined commands.
- Keep total content tight enough to fit one page.

BASE RESUME:
{base_resume}

GITHUB PROJECT SUMMARY:
{github_summary}

TARGET JOB DESCRIPTION:
{job_description}

Output ONLY the complete LaTeX document, starting with \\documentclass and
ending with \\end{{document}}. No commentary, no markdown fences."""
        return self._clean_latex(self._generate(prompt))