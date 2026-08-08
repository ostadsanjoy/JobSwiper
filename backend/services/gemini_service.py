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

    def map_application_fields(
        self, fields: list, resume_text: str, cover_letter: str, profile: dict = None
    ) -> dict:
        profile_facts = json.dumps(profile or {}, indent=2)
        prompt = f"""You are an AI Job Application Agent filling out an online job application form.

Candidate Ground Truth Profile Facts:
{profile_facts}

Candidate Tailored Resume:
{resume_text}

Candidate Cover Letter:
{cover_letter}

Form Fields Detected on Application Page:
{json.dumps(fields, indent=2)}

INSTRUCTIONS:
1. For contact info (Name, Email, Phone, Location, LinkedIn, GitHub, Portfolio): use Ground Truth Profile Facts.
2. For Work Authorization, Visa Sponsorship, Expected Salary, Notice Period questions: use Ground Truth Profile Facts.
3. For resume file upload fields: set action="upload_resume", value=""
4. For cover letter textareas: set action="fill", value=candidate cover letter
5. For dropdown select fields: choose the option text that best matches candidate profile.

Output ONLY valid JSON:
{{
  "actions": {{
    "field_id": {{"action": "fill", "value": "text..."}}
  }}
}}"""
        return self._generate_json(prompt)

    # ── Role domain detection ────────────────────────────────────────────
    # Maps keyword patterns to domain IDs.  Order matters: first match wins
    # within a priority tier, but we scan ALL and pick the best-matching
    # domain by hit count so "Senior Data Scientist" → data_science, not
    # engineering.

    _DOMAIN_KEYWORDS = {
        "engineering": [
            "software engineer", "software developer", "backend engineer",
            "frontend engineer", "fullstack", "full stack", "full-stack",
            "devops", "sre", "site reliability", "platform engineer",
            "mobile developer", "ios developer", "android developer",
            "embedded engineer", "systems engineer", "web developer",
            "cloud engineer", "infrastructure engineer",
        ],
        "data_science": [
            "data scientist", "machine learning engineer", "ml engineer",
            "ai researcher", "deep learning", "nlp engineer",
            "computer vision", "research scientist", "applied scientist",
        ],
        "product": [
            "product manager", "product owner", "program manager",
            "technical program manager", "tpm", "product lead",
        ],
        "design": [
            "ux designer", "ui designer", "product designer",
            "visual designer", "interaction designer", "design lead",
        ],
        "sales": [
            "account manager", "account executive", "sales representative",
            "sales engineer", "business development", "sdr",
            "sales manager", "revenue", "quota", "deal cycle",
            "enterprise account", "strategic account", "renewals",
            "commercial negotiations", "churn", "upsell",
        ],
        "marketing": [
            "marketing manager", "growth manager", "content strategist",
            "seo", "demand generation", "brand manager", "social media manager",
        ],
        "finance": [
            "financial analyst", "quantitative analyst", "quant",
            "trader", "investment banking", "comptroller", "actuary",
            "risk analyst", "portfolio manager",
        ],
        "management": [
            "vp of engineering", "vp engineering", "director of engineering",
            "engineering manager", "head of engineering", "cto",
            "chief technology officer", "head of product", "vp product",
        ],
        "operations": [
            "operations manager", "supply chain", "logistics manager",
            "procurement", "warehouse manager",
        ],
        "support": [
            "customer success", "support engineer", "technical support",
            "customer support", "solutions engineer", "solutions architect",
        ],
    }

    # Realistic cross-domain transferability scores (0-100).
    # Read as: candidate FROM row domain → applying TO column domain.
    _DOMAIN_COMPAT = {
        #                     eng  ds   prod des  sale mkt  fin  mgmt ops  sup  gen
        "engineering":       [100, 70,  65,  30,  15,  20,  40,  50,  25,  55,  50],
        "data_science":      [65,  100, 55,  15,  15,  30,  70,  45,  20,  30,  50],
        "product":           [35,  35,  100, 50,  45,  55,  30,  65,  45,  40,  50],
        "design":            [20,  15,  55,  100, 15,  45,  10,  30,  15,  25,  50],
        "sales":             [10,  10,  40,  10,  100, 55,  35,  50,  40,  50,  50],
        "marketing":         [15,  20,  50,  40,  50,  100, 20,  40,  30,  35,  50],
        "finance":           [25,  55,  35,  10,  30,  20,  100, 45,  35,  20,  50],
        "management":        [45,  40,  60,  30,  45,  40,  40,  100, 50,  40,  50],
        "operations":        [20,  15,  40,  15,  40,  30,  30,  45,  100, 40,  50],
        "support":           [40,  25,  40,  20,  45,  30,  20,  35,  35,  100, 50],
        "general":           [50,  50,  50,  50,  50,  50,  50,  50,  50,  50,  50],
    }
    _DOMAIN_ORDER = [
        "engineering", "data_science", "product", "design", "sales",
        "marketing", "finance", "management", "operations", "support", "general",
    ]

    # Seniority tiers (lowest → highest)
    _SENIORITY_TIERS = [
        (["intern", "trainee", "apprentice"], 0),
        (["junior", "jr.", "entry level", "entry-level", "associate", "graduate"], 1),
        (["mid", "mid-level", "mid level"], 2),
        (["senior", "sr.", "sr "], 3),
        (["staff", "lead", "principal", "team lead"], 4),
        (["director", "head of", "vp", "vice president"], 5),
        (["c-suite", "cto", "ceo", "cfo", "coo", "chief"], 6),
    ]

    KNOWN_TECH_SKILLS = {
        # Hard tech
        "aem": "AEM (Adobe Experience Manager)",
        "java": "Java",
        "python": "Python",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "react": "React",
        "node.js": "Node.js",
        "pytorch": "PyTorch",
        "tensorflow": "TensorFlow",
        "fastapi": "FastAPI",
        "django": "Django",
        "flask": "Flask",
        "spring": "Spring Boot",
        "sql": "SQL",
        "postgresql": "PostgreSQL",
        "mongodb": "MongoDB",
        "redis": "Redis",
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "aws": "AWS",
        "gcp": "Google Cloud",
        "azure": "Azure",
        "graphql": "GraphQL",
        "restful": "REST APIs",
        "rest api": "REST APIs",
        "git": "Git",
        "ci/cd": "CI/CD",
        "machine learning": "Machine Learning",
        "deep learning": "Deep Learning",
        "nlp": "NLP",
        "html": "HTML",
        "css": "CSS",
        "vue.js": "Vue.js",
        "vuejs": "Vue.js",
        "next.js": "Next.js",
        "c++": "C++",
        "golang": "Go/Golang",
        "rust": "Rust",
        "php": "PHP",
        "ruby": "Ruby",
        "kotlin": "Kotlin",
        "swift": "Swift",
        "scala": "Scala",
        # Functional / soft — lets cross-domain candidates score on real skills
        "agile": "Agile",
        "scrum": "Scrum",
        "jira": "Jira",
        "confluence": "Confluence",
        "figma": "Figma",
        "tableau": "Tableau",
        "power bi": "Power BI",
        "excel": "Excel",
        "stakeholder management": "Stakeholder Management",
        "product management": "Product Management",
        "project management": "Project Management",
        "data analysis": "Data Analysis",
        "financial modeling": "Financial Modeling",
        "analytics": "Analytics",
        "statistics": "Statistics",
        "a/b testing": "A/B Testing",
        "user research": "User Research",
        "negotiation": "Negotiation",
        "budgeting": "Budgeting",
        "forecasting": "Forecasting",
    }

    # Keywords that signal a candidate has exposure to a target domain,
    # even if their primary domain is different (eng student with PM keywords
    # → domain boost toward product, math grad with finance keywords → boost).
    # ponytail: flat dict is simpler than nested; each list is short.
    _DOMAIN_BOOST_KEYWORDS = {
        "product": ["product roadmap", "user stories", "stakeholder", "product strategy",
                    "product management", "user research", "a/b testing", "prioritization"],
        "finance": ["financial modeling", "risk analysis", "valuation", "portfolio",
                    "quantitative", "derivatives", "forecasting", "budgeting"],
        "data_science": ["machine learning", "deep learning", "pytorch", "tensorflow",
                         "data pipeline", "feature engineering", "model training"],
        "engineering": ["software engineer", "full stack", "backend", "frontend",
                        "api", "microservices", "ci/cd", "docker"],
        "design": ["figma", "wireframe", "user experience", "prototyping",
                   "design system", "usability"],
        "marketing": ["seo", "content strategy", "demand generation", "growth",
                      "campaign", "brand"],
        "sales": ["pipeline", "quota", "crm", "deal cycle", "enterprise sales",
                  "account management"],
        "management": ["team lead", "engineering manager", "people management",
                       "mentoring", "cross-functional"],
    }

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _skill_in_text(skill_key: str, text_lower: str) -> bool:
        """Word-boundary skill match. Prevents 'go' matching 'going',
        'rest' matching 'interest', 'excel' matching 'excellent', etc.
        ponytail: re.escape handles c++, ci/cd, a/b testing safely."""
        return bool(re.search(r'\b' + re.escape(skill_key) + r'\b', text_lower))

    @staticmethod
    def _detect_domain(text: str) -> str:
        """Return the best-matching domain ID for a blob of text."""
        text_lower = text.lower()
        hits: dict[str, int] = {}
        for domain, keywords in GeminiService._DOMAIN_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count:
                hits[domain] = count
        if not hits:
            return "general"
        return max(hits, key=hits.get)

    @staticmethod
    def _domain_compat_score(from_domain: str, to_domain: str) -> int:
        row = GeminiService._DOMAIN_COMPAT.get(from_domain, GeminiService._DOMAIN_COMPAT["general"])
        try:
            col_idx = GeminiService._DOMAIN_ORDER.index(to_domain)
        except ValueError:
            col_idx = GeminiService._DOMAIN_ORDER.index("general")
        return row[col_idx]

    @staticmethod
    def _contextual_domain_boost(candidate_text: str, target_domain: str) -> int:
        """Boost domain score when candidate text contains target-domain keywords.
        Returns 0-25 bonus points.  ponytail: linear scale, no magic."""
        keywords = GeminiService._DOMAIN_BOOST_KEYWORDS.get(target_domain, [])
        if not keywords:
            return 0
        text_lower = candidate_text.lower()
        hits = sum(1 for kw in keywords if kw in text_lower)
        # Each hit = ~6 pts, capped at 25
        return min(25, hits * 6)

    @staticmethod
    def _extract_required_years(text: str) -> int | None:
        """Pull the highest 'N+ years' requirement from a JD."""
        patterns = [
            r"(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)",
            r"minimum\s+(\d+)\s*(?:years?|yrs?)",
            r"at\s+least\s+(\d+)\s*(?:years?|yrs?)",
            r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:full|relevant|professional|industry|hands-on|direct)",
            r"(\d+)\s*-\s*\d+\s*(?:years?|yrs?)",
            # "6+ years in engineering", "3+ years as a Golang engineer"
            r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:in|as|of)\s+(?:a\s+)?(?:sales|account|management|engineering|software|development|design|marketing|product|data|finance|devops|cloud|mobile|frontend|backend|fullstack)",
        ]
        found = []
        for pat in patterns:
            for m in re.finditer(pat, text.lower()):
                found.append(int(m.group(1)))
        return max(found) if found else None

    @staticmethod
    def _extract_candidate_years(text: str) -> int | None:
        """Estimate candidate experience years from resume text."""
        # Direct claim: "X years of experience"
        m = re.search(r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)", text.lower())
        if m:
            return int(m.group(1))
        # Count distinct year ranges like "2020-2023", "Jan 2021 – Present"
        year_mentions = [int(y) for y in re.findall(r"(?:19|20)\d{2}", text)]
        if len(year_mentions) >= 2:
            span = max(year_mentions) - min(year_mentions)
            if 0 < span <= 50:
                return span
        return None

    @staticmethod
    def _detect_seniority_tier(text: str) -> int:
        """Return a seniority tier int (0=intern … 6=C-suite)."""
        text_lower = text.lower()
        best = 2  # default: mid-level
        for keywords, tier in GeminiService._SENIORITY_TIERS:
            for kw in keywords:
                if kw in text_lower:
                    best = max(best, tier)
        return best

    # ── LLM-based evaluator (per-job detail view) ─────────────────────────

    def evaluate_job_match(
        self, job_title: str, job_description: str, resume_text: str
    ) -> dict:
        if not resume_text:
            return {
                "score": 0,
                "badge": "Upload Resume",
                "matching_skills": [],
                "missing_skills": [],
                "portfolio_gaps": ["Upload resume to analyze portfolio gaps"],
                "work_auth_fit": "Unknown",
            }
        prompt = f"""You are a brutally honest senior talent evaluator. Analyze how
well the candidate ACTUALLY fits the target role. You must evaluate FOUR
dimensions and be realistic about each:

1. ROLE DOMAIN FIT: Is the candidate's career track (e.g. software
   engineering, sales, marketing, finance, product, design) compatible
   with this role's domain? A software engineer is NOT a fit for an
   Enterprise Sales Manager role even if the company name appears on
   their resume. However, reasonable cross-domain transitions ARE valid
   (e.g. engineer → product manager, math grad → quant finance) IF the
   candidate has relevant transferable experience.

2. EXPERIENCE LEVEL: Does the candidate meet the years-of-experience
   requirement? If the JD asks for 8+ years and the candidate has 0-2
   years, score MUST be very low (under 20) regardless of other factors.
   A student or fresh graduate cannot match a role requiring 6+ years of
   enterprise deal cycles.

3. TECHNICAL / FUNCTIONAL SKILLS: Do the candidate's specific skills
   match what the role requires? Consider both hard skills (languages,
   tools) and functional skills (negotiation, stakeholder management,
   account planning).

4. SENIORITY FIT: Does the candidate's career level match the role level?
   An intern/student profile does not match a Director-level role.

CRITICAL: Do NOT inflate scores based on keyword overlap alone. A
candidate having "Stripe" on their resume does not make them a fit for
a Stripe Enterprise Sales role if they are a software engineering student.
Location is NOT a factor - people can relocate.

JOB TITLE: {job_title}

JOB DESCRIPTION:
{job_description[:3000]}

CANDIDATE RESUME:
{resume_text[:3000]}

Output ONLY valid JSON:
{{
  "score": <integer 0-100>,
  "badge": <"Strong Fit" | "Good Match" | "Moderate Fit" | "Low Fit">,
  "matching_skills": [<up to 4 relevant matching skills or transferable strengths>],
  "missing_skills": [<up to 3 critical missing requirements>],
  "portfolio_gaps": [<up to 3 specific gaps or action items>],
  "work_auth_fit": <short work authorization summary>
}}"""
        try:
            return self._generate_json(prompt)
        except Exception:
            return self.compute_fast_match_score(job_title, job_description, resume_text)

    # ── Fast heuristic scorer (called for every job in search) ────────────

    def compute_fast_match_score(
        self, job_title: str, job_description: str, candidate_resume: str,
        candidate_profile: dict = None, github_repos: list = None,
    ) -> dict:
        profile_data = candidate_profile or {}
        repo_list = github_repos or []
        combined_candidate = " ".join([
            profile_data.get("full_name", ""),
            profile_data.get("expected_salary", ""),
            profile_data.get("work_auth", ""),
            profile_data.get("sponsorship_req", ""),
            candidate_resume or "",
            " ".join(repo_list),
        ]).lower()

        if not combined_candidate.strip():
            return {
                "score": 0,
                "badge": "Upload Resume",
                "matching_skills": [],
                "missing_skills": [],
                "portfolio_gaps": ["Upload resume & Candidate Vault to evaluate fit"],
                "work_auth_fit": "Unknown",
            }

        title_lower = (job_title or "").lower()
        desc_lower = (job_description or "").lower()
        blob_lower = f"{title_lower} {desc_lower}"

        # ── Dimension 1: Role Domain Compatibility (30%) ──────────────
        jd_domain = self._detect_domain(f"{job_title or ''} {job_description or ''}")
        candidate_domain = self._detect_domain(combined_candidate)
        domain_score = self._domain_compat_score(candidate_domain, jd_domain)
        # Contextual boost: engineer with PM keywords on resume → bump
        domain_score = min(100, domain_score + self._contextual_domain_boost(combined_candidate, jd_domain))

        # ── Dimension 2: Experience Level Fit (25%) ───────────────────
        jd_required_years = self._extract_required_years(blob_lower)
        candidate_years = self._extract_candidate_years(combined_candidate)

        if jd_required_years is not None and candidate_years is not None:
            gap = jd_required_years - candidate_years
            if gap <= 0:
                experience_score = 100
            elif gap <= 2:
                experience_score = 70
            elif gap <= 4:
                experience_score = 40
            else:
                experience_score = 15
        elif jd_required_years is not None and candidate_years is None:
            # JD asks for experience but we can't determine candidate's → penalize
            experience_score = 35 if jd_required_years >= 5 else 50
        else:
            # No years requirement in JD or can't parse either → neutral
            experience_score = 70

        # ── Dimension 3: Skill Overlap (30%) ──────────────────────────
        # Now includes functional/soft skills, not just hard tech
        jd_skill_requirements = []
        for key, display_name in self.KNOWN_TECH_SKILLS.items():
            if self._skill_in_text(key, blob_lower):
                jd_skill_requirements.append((key, display_name))

        matching_skills = []
        missing_skills = []
        for key, display_name in jd_skill_requirements:
            if self._skill_in_text(key, combined_candidate):
                matching_skills.append(display_name)
            else:
                missing_skills.append(display_name)

        if jd_skill_requirements:
            match_ratio = len(matching_skills) / len(jd_skill_requirements)
            skills_score = int(match_ratio * 100)
        else:
            # Role doesn't mention any tracked skills — neutral
            skills_score = 50

        # ── Dimension 4: Seniority Title Fit (15%) ────────────────────
        jd_seniority = self._detect_seniority_tier(title_lower)
        candidate_seniority = self._detect_seniority_tier(combined_candidate)
        tier_gap = abs(jd_seniority - candidate_seniority)

        if tier_gap == 0:
            seniority_score = 100
        elif tier_gap == 1:
            seniority_score = 70
        elif tier_gap == 2:
            seniority_score = 40
        else:
            seniority_score = 15

        # ── Weighted combination ──────────────────────────────────────
        # ponytail: weights sum to 1.0 — domain 30%, exp 25%, skills 30%, seniority 15%
        raw_score = int(
            domain_score * 0.30
            + experience_score * 0.25
            + skills_score * 0.30
            + seniority_score * 0.15
        )
        raw_score = max(0, min(100, raw_score))

        # ── Portfolio gaps & missing-skills context ───────────────────
        portfolio_gaps = []

        if domain_score < 40:
            portfolio_gaps.append(
                f"Domain mismatch: your background is {candidate_domain.replace('_', ' ')}, "
                f"role is {jd_domain.replace('_', ' ')}"
            )

        if jd_required_years and candidate_years is not None:
            gap = jd_required_years - candidate_years
            if gap > 2:
                portfolio_gaps.append(
                    f"Experience gap: role requires {jd_required_years}+ yrs, "
                    f"you have ~{candidate_years} yrs"
                )
                missing_skills.insert(0, f"{jd_required_years}+ Yrs Experience")

        if jd_required_years and candidate_years is None and jd_required_years >= 5:
            portfolio_gaps.append(
                f"Role requires {jd_required_years}+ years experience — "
                f"could not determine your experience level"
            )

        if tier_gap >= 2:
            portfolio_gaps.append(
                "Seniority gap: role level does not match your career stage"
            )

        # Education gap (informational, not scored)
        if "master" in desc_lower or "m.s." in desc_lower or "phd" in desc_lower:
            if not any(e in combined_candidate for e in ["master", "m.s.", "phd", "doctorate"]):
                portfolio_gaps.append("Education: JD mentions Master's / Ph.D. preference")

        if not portfolio_gaps:
            portfolio_gaps.append("Solid alignment with role requirements")

        # ── Badges ────────────────────────────────────────────────────
        if raw_score >= 75:
            badge = "Strong Fit"
        elif raw_score >= 55:
            badge = "Good Match"
        elif raw_score >= 35:
            badge = "Moderate Fit"
        else:
            badge = "Low Fit"

        # ── Work Auth (informational only, not scored) ────────────────
        sponsorship_val = profile_data.get("sponsorship_req", "")
        work_auth_fit = "Authorized"
        if "visa" in desc_lower or "sponsorship" in desc_lower:
            if "sponsorship required" in sponsorship_val.lower():
                work_auth_fit = "Visa Sponsorship Required"
            else:
                work_auth_fit = "No Sponsorship Needed"

        return {
            "score": raw_score,
            "badge": badge,
            "matching_skills": list(dict.fromkeys(matching_skills))[:4],
            "missing_skills": list(dict.fromkeys(missing_skills))[:3],
            "portfolio_gaps": portfolio_gaps[:3],
            "work_auth_fit": work_auth_fit,
        }





    def analyze_portfolio_gaps(
        self, resume_text: str, github_summary: str
    ) -> dict:
        prompt = f"""You are an elite Tech Career Lead and Hiring Director. Analyze the candidate's active resume and GitHub portfolio context below. Identify key strengths, critical gaps, and high-impact immediate recommendations.

CANDIDATE RESUME:
{resume_text[:4000] if resume_text else "No resume uploaded yet."}

GITHUB PORTFOLIO CONTEXT:
{github_summary[:4000] if github_summary else "No GitHub projects fetched."}

Provide a realistic, actionable career gap analysis as valid JSON:
- "strengths": Array of 2-4 key technical strengths.
- "critical_gaps": Array of 2-4 missing industry skills or project types.
- "immediate_focus": Array of 2-3 specific actionable projects/features to build next.
- "summary_verdict": Short 1-2 sentence overall summary verdict.

Output ONLY valid JSON:
{{
  "strengths": ["Strong frontend experience with React & Vite", "Real-world project portfolio"],
  "critical_gaps": ["Lacks experience with Docker containerization", "No unit test suites in public repos"],
  "immediate_focus": ["Add Dockerfile and CI/CD GitHub Action to top repo", "Build a service demonstrating Redis caching"],
  "summary_verdict": "Solid technical foundation. Adding production DevOps tooling will boost recruiter callbacks."
}}"""
        try:
            return self._generate_json(prompt)
        except Exception as e:
            return {
                "strengths": ["Active developer"],
                "critical_gaps": ["Upload resume for full AI analysis"],
                "immediate_focus": ["Upload a PDF resume in Account tab"],
                "summary_verdict": f"Analysis pending: {e}",
            }
