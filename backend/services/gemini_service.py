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

    def tailor_resume(self, base_resume: str, job_description: str, github_summary: str) -> str:
        prompt = f"""You are a resume editor. Rewrite the resume below so it is
tailored to the target job description. Keep it truthful - do not invent
experience, employers, or skills that aren't supported by the base resume or
the GitHub summary. Reorder and reword bullet points to emphasize relevant
experience, mirror relevant keywords from the job description naturally, and
keep the same overall format and length as the original.

BASE RESUME:
{base_resume}

GITHUB ACTIVITY SUMMARY (for context on real projects/skills):
{github_summary}

TARGET JOB DESCRIPTION:
{job_description}

Output only the tailored resume text, no commentary."""
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

Use empty strings for any contact fields not present in the source resume.
For a skills section, put the skill list as a single bullet in one entry
with empty title/subtitle/dates. Preserve all real content from the source
resume - do not drop bullets, do not invent new ones.

SOURCE RESUME:
{tailored_resume_text}"""
        return self._generate_json(prompt)