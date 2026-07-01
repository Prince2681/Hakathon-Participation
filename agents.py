# agents.py - CareerPilot AI v3
# Lemma/Lemme-aware agent runtime with universal job matching fallback.

import json
import time
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger("careerpilot")
_client = None
_runtime = "demo"


class _RuntimeClient:
    def __init__(self, kind, client=None, agent_cls=None):
        self.kind = kind
        self.client = client
        self.agent_cls = agent_cls


def set_api_key(key: str):
    """Configure the best available runtime: Lemma/Lemme first, then OpenAI, then demo."""
    global _client, _runtime
    if not key:
        _client = None
        _runtime = "demo"
        return

    os.environ["LEMMA_API_KEY"] = key
    os.environ["LEMME_API_KEY"] = key
    os.environ["OPENAI_API_KEY"] = key

    for module_name in ("lemma", "lemme"):
        try:
            mod = __import__(module_name)
            agent_cls = getattr(mod, "Agent", None)
            if agent_cls:
                _client = _RuntimeClient(module_name, agent_cls=agent_cls)
                _runtime = module_name
                logger.info("%s Agent runtime set", module_name)
                return
        except Exception as exc:
            logger.debug("%s runtime unavailable: %s", module_name, exc)

    try:
        from openai import OpenAI
        _client = _RuntimeClient("openai", client=OpenAI(api_key=key))
        _runtime = "openai"
        logger.info("OpenAI runtime set")
    except Exception as exc:
        logger.warning("No hosted AI runtime available; using demo fallback: %s", exc)
        _client = None
        _runtime = "demo"


def get_runtime_status() -> dict:
    return {
        "runtime": _runtime,
        "active": _client is not None,
        "lemma_aligned": _runtime in {"lemma", "lemme"},
        "fallback": "deterministic universal demo" if _client is None else None,
    }


def _normalise_response(resp) -> str:
    if resp is None:
        return ""
    if isinstance(resp, str):
        return resp.strip()
    for attr in ("content", "text", "output", "response"):
        value = getattr(resp, attr, None)
        if value:
            return str(value).strip()
    if isinstance(resp, dict):
        for key in ("content", "text", "output", "response"):
            if resp.get(key):
                return str(resp[key]).strip()
    return str(resp).strip()


def _call(system: str, user: str, expect_json: bool = True, agent_type: str = "generic") -> str:
    """Core AI call. Uses Lemma/Lemme when installed, OpenAI next, universal fallback last."""
    if not _client:
        return _mock(expect_json, agent_type, user)
    try:
        if _client.kind in {"lemma", "lemme"}:
            agent = _client.agent_cls(instructions=system)
            if hasattr(agent, "run"):
                result = agent.run(user)
            elif hasattr(agent, "complete"):
                result = agent.complete(user)
            else:
                raise RuntimeError("Lemma/Lemme Agent has no run/complete method")
            raw = _normalise_response(result)
        else:
            resp = _client.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            raw = resp.choices[0].message.content.strip()
        return raw.replace("```json", "").replace("```", "").strip()
    except Exception as e:
        logger.error("AI call failed; using universal fallback: %s", e)
        return _mock(expect_json, agent_type, user)


SKILL_ALIASES = {
    "Python": ["python", "pandas", "numpy", "scikit", "matplotlib", "seaborn"],
    "SQL": ["sql", "mysql", "postgres", "postgresql", "sqlite", "query"],
    "Excel": ["excel", "spreadsheet", "vlookup", "pivot table"],
    "Power BI": ["power bi", "powerbi"],
    "Tableau": ["tableau"],
    "Machine Learning": ["machine learning", "ml", "model training", "predictive model"],
    "Statistics": ["statistics", "statistical", "hypothesis", "regression"],
    "JavaScript": ["javascript", "typescript", "node.js", "nodejs", "react", "next.js", "vue", "angular"],
    "Java": ["java", "spring", "spring boot"],
    "C++": ["c++", "cpp"],
    "C#": ["c#", ".net", "dotnet"],
    "Django": ["django"],
    "Flask": ["flask"],
    "FastAPI": ["fastapi"],
    "React": ["react", "redux", "next.js"],
    "AWS": ["aws", "amazon web services", "lambda", "s3", "ec2"],
    "Azure": ["azure"],
    "GCP": ["gcp", "google cloud"],
    "Docker": ["docker", "container"],
    "Kubernetes": ["kubernetes", "k8s"],
    "CI/CD": ["ci/cd", "jenkins", "github actions", "gitlab ci"],
    "System Design": ["system design", "distributed systems", "scalable"],
    "APIs": ["api", "rest", "graphql", "microservice"],
    "Testing": ["testing", "qa", "selenium", "pytest", "unit test", "automation testing"],
    "Agile": ["agile", "scrum", "kanban", "sprint"],
    "Jira": ["jira", "confluence"],
    "Roadmapping": ["roadmap", "roadmapping", "product strategy"],
    "User Research": ["user research", "customer discovery", "usability"],
    "Stakeholder Management": ["stakeholder", "cross-functional", "alignment"],
    "Figma": ["figma", "sketch", "adobe xd"],
    "Prototyping": ["prototype", "wireframe", "mockup"],
    "Design Systems": ["design system", "component library"],
    "SEO": ["seo", "search engine optimization"],
    "SEM": ["sem", "paid search", "google ads", "ppc"],
    "Google Analytics": ["google analytics", "ga4"],
    "HubSpot": ["hubspot"],
    "Content Marketing": ["content marketing", "content strategy", "copywriting"],
    "Social Media": ["social media", "instagram", "linkedin", "twitter", "facebook"],
    "Campaign Management": ["campaign", "campaign management", "marketing automation"],
    "Salesforce": ["salesforce"],
    "CRM": ["crm", "zoho", "hubspot crm"],
    "B2B Sales": ["b2b", "enterprise sales", "account executive"],
    "Negotiation": ["negotiation", "closing", "quota"],
    "Financial Modelling": ["financial model", "financial modelling", "valuation", "dcf"],
    "FP&A": ["fp&a", "forecasting", "budgeting", "variance analysis"],
    "Accounting": ["accounting", "ledger", "reconciliation", "gaap", "ifrs"],
    "Recruitment": ["recruitment", "talent acquisition", "sourcing", "screening"],
    "Payroll": ["payroll", "compensation", "benefits"],
    "HRMS": ["hrms", "hris", "workday"],
    "Operations": ["operations", "process improvement", "supply chain", "logistics"],
    "Customer Support": ["customer support", "customer service", "ticketing", "zendesk"],
    "Communication": ["communication", "presentation", "written", "verbal", "collaboration"],
    "Leadership": ["leadership", "managed team", "mentoring", "people management"],
    "Problem Solving": ["problem solving", "analytical", "troubleshooting", "critical thinking"],
}

ROLE_RULES = {
    "Data / Analytics": ["data analyst", "data scientist", "analytics", "dashboard", "business intelligence", "machine learning", "sql", "power bi", "tableau"],
    "Software Engineering": ["software engineer", "developer", "backend", "frontend", "full stack", "java", "python", "react", "api", "microservice"],
    "DevOps / Cloud": ["devops", "site reliability", "sre", "cloud engineer", "aws", "docker", "kubernetes", "terraform", "ci/cd"],
    "QA / Testing": ["qa", "quality assurance", "test engineer", "automation testing", "selenium", "manual testing"],
    "Product Management": ["product manager", "product owner", "roadmap", "backlog", "user stories", "go-to-market", "product strategy"],
    "Design": ["ux", "ui", "product designer", "graphic designer", "figma", "wireframe", "prototype"],
    "Marketing": ["marketing", "seo", "sem", "campaign", "content", "social media", "brand", "google analytics"],
    "Sales": ["sales", "account executive", "business development", "lead generation", "pipeline", "quota", "crm"],
    "Finance": ["finance", "financial analyst", "accounting", "fp&a", "budget", "forecast", "valuation"],
    "Human Resources": ["hr", "human resources", "recruiter", "talent acquisition", "payroll", "employee relations"],
    "Operations": ["operations", "program coordinator", "supply chain", "logistics", "process improvement", "vendor management"],
    "Customer Success": ["customer success", "account manager", "customer support", "retention", "onboarding", "zendesk"],
    "Legal / Compliance": ["legal", "compliance", "contract", "policy", "risk", "regulatory"],
    "Healthcare": ["nurse", "clinical", "healthcare", "patient", "medical", "pharma"],
    "Education": ["teacher", "trainer", "curriculum", "instructional", "learning", "education"],
}

STOPWORDS = {"and", "or", "with", "for", "the", "a", "an", "to", "of", "in", "on", "at", "by", "from", "as", "is", "are", "be", "will", "must", "should", "years", "experience", "strong", "good", "excellent", "knowledge"}


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _section(prompt: str, heading: str, stops=None) -> str:
    stops = stops or []
    pattern = re.escape(heading) + r"\s*:\s*"
    m = re.search(pattern, prompt, re.I)
    if not m:
        return ""
    start = m.end()
    end = len(prompt)
    for stop in stops:
        sm = re.search(r"\n" + re.escape(stop) + r"\s*:\s*", prompt[start:], re.I)
        if sm:
            end = min(end, start + sm.start())
    return prompt[start:end].strip()


def _has_phrase(text_lower: str, phrase: str) -> bool:
    phrase = phrase.lower().strip()
    if any(ch in phrase for ch in "+#./"):
        return phrase in text_lower
    return re.search(r"\b" + re.escape(phrase) + r"\b", text_lower) is not None


def _extract_skills(text: str) -> list:
    low = text.lower()
    found = []
    for canonical, aliases in SKILL_ALIASES.items():
        if any(_has_phrase(low, alias) for alias in aliases):
            found.append(canonical)
    return found


def _detect_role(text: str) -> str:
    low = text.lower()
    best_role = "General"
    best_score = 0
    for role, keywords in ROLE_RULES.items():
        score = sum(3 if " " in kw and _has_phrase(low, kw) else 1 if _has_phrase(low, kw) else 0 for kw in keywords)
        if score > best_score:
            best_role, best_score = role, score
    return best_role


def _extract_title(jd_text: str, fallback_role="General") -> str:
    lines = [_clean_text(x) for x in jd_text.splitlines() if _clean_text(x)]
    for line in lines[:8]:
        if re.search(r"\b(role|title|position|opening|job)\b", line, re.I) and len(line) < 100:
            return re.sub(r"^(role|title|position|job|opening)\s*[:\-]\s*", "", line, flags=re.I).strip()
    for line in lines[:5]:
        if 3 <= len(line) <= 80 and not line.lower().startswith(("company", "about", "we are")):
            return line
    return fallback_role if fallback_role != "General" else "Role"


def _extract_company(jd_text: str) -> str:
    for line in jd_text.splitlines()[:12]:
        m = re.search(r"(?:company|organisation|organization)\s*[:\-]\s*([^\n,|]+)", line, re.I)
        if m:
            return _clean_text(m.group(1))[:60]
    return "Unknown"


def _detect_seniority(text: str) -> str:
    low = text.lower()
    if any(x in low for x in ["intern", "internship"]): return "Intern"
    if any(x in low for x in ["fresher", "entry level", "graduate trainee"]): return "Fresher"
    if any(x in low for x in ["lead", "principal", "staff"]): return "Lead"
    if any(x in low for x in ["manager", "head of", "director"]): return "Manager"
    if any(x in low for x in ["senior", "sr.", "sr "]): return "Senior"
    if any(x in low for x in ["junior", "jr.", "associate"]): return "Junior"
    return "Mid"


def _keyword_candidates(text: str) -> list:
    skills = _extract_skills(text)
    low = text.lower()
    extra = []
    for pat in [r"(?:experience with|knowledge of|required skills?:|must have|tools?:)\s*([^\.\n]+)", r"\b(?:using|in)\s+([A-Z][A-Za-z0-9+#./ -]{1,35})"]:
        for m in re.finditer(pat, text, re.I):
            chunk = m.group(1)
            for part in re.split(r",|/|\band\b|\bor\b", chunk):
                item = _clean_text(part).strip(" .;:-")
                if 2 <= len(item) <= 35 and item.lower() not in STOPWORDS and not item.lower().startswith(("the ", "a ")):
                    extra.append(item)
    # Preserve order and keep reasonable list.
    return list(dict.fromkeys(skills + extra))[:16]


def _responsibilities(jd_text: str, role: str) -> list:
    lines = [_clean_text(x).strip("-?* ") for x in jd_text.splitlines()]
    picked = [x for x in lines if 20 <= len(x) <= 160 and re.search(r"\b(manage|build|design|develop|lead|create|analyse|analyze|coordinate|support|drive|own|prepare|maintain|sell|recruit)\b", x, re.I)]
    if picked:
        return picked[:3]
    return [f"Perform core {role.lower()} responsibilities", "Collaborate with stakeholders", "Deliver measurable outcomes"]


def _offline_resume(resume_text: str) -> dict:
    skills = _extract_skills(resume_text)
    role = _detect_role(resume_text)
    years = 0
    nums = [int(x) for x in re.findall(r"(\d+)\+?\s*(?:years|yrs)", resume_text, re.I)]
    if nums:
        years = max(nums)
    name = "Candidate"
    first_line = next((_clean_text(x) for x in resume_text.splitlines() if _clean_text(x)), "")
    if first_line and len(first_line) < 80 and not any(k in first_line.lower() for k in ["resume", "curriculum", "email", "phone"]):
        name = first_line
    score = min(95, 45 + len(skills) * 4 + min(years, 10) * 2)
    return {
        "name": name,
        "current_role": role,
        "experience_years": years,
        "education": "Detected from resume" if re.search(r"\b(b\.?tech|bachelor|master|mba|degree|university|college)\b", resume_text, re.I) else "Unknown",
        "all_skills": skills,
        "top_skills": skills[:5],
        "industry": role,
        "resume_score": score,
        "summary": f"{role} candidate with {years} years of experience and skills in {', '.join(skills[:4]) or 'role-relevant areas'}."
    }


def _offline_jd(jd_text: str) -> dict:
    role = _detect_role(jd_text)
    skills = _keyword_candidates(jd_text)
    required = skills[:8]
    nice = skills[8:13]
    return {
        "company": _extract_company(jd_text),
        "role_title": _extract_title(jd_text, role),
        "seniority": _detect_seniority(jd_text),
        "role_category": role,
        "required_skills": required,
        "nice_to_have_skills": nice,
        "key_responsibilities": _responsibilities(jd_text, role),
        "ats_keywords": list(dict.fromkeys(required + nice))[:12],
        "industry": role,
    }


def _skill_match(resume_skills: list, jd_skill: str, resume_text_lower: str) -> bool:
    jd_low = jd_skill.lower()
    if any(jd_low == s.lower() for s in resume_skills):
        return True
    aliases = SKILL_ALIASES.get(jd_skill, [jd_skill])
    return any(_has_phrase(resume_text_lower, alias) for alias in aliases) or any(jd_low in s.lower() or s.lower() in jd_low for s in resume_skills if len(s) > 2)


def _offline_match(resume_text: str, jd_text: str, jd_data=None) -> dict:
    jd_data = jd_data or _offline_jd(jd_text)
    resume_profile = _offline_resume(resume_text)
    resume_skills = resume_profile["all_skills"]
    req = list(dict.fromkeys(jd_data.get("required_skills", []) + jd_data.get("nice_to_have_skills", [])[:3]))
    resume_low = resume_text.lower()
    matched = [s for s in req if _skill_match(resume_skills, s, resume_low)]
    missing = [s for s in req if s not in matched]
    required_count = max(1, len(jd_data.get("required_skills", req)) or len(req) or 1)
    req_matched = len([s for s in jd_data.get("required_skills", req) if s in matched])
    skill_score = round((len(matched) / max(1, len(req))) * 100) if req else 35
    required_score = round((req_matched / required_count) * 100)
    role_bonus = 12 if jd_data.get("role_category") != "General" and jd_data.get("role_category") == resume_profile.get("current_role") else 0
    fit = max(5, min(100, round(skill_score * 0.55 + required_score * 0.35 + role_bonus)))
    ats = max(0, min(100, round((len(matched) / max(1, len(jd_data.get("ats_keywords", req)))) * 100)))
    priority = "High" if fit >= 75 else "Medium" if fit >= 45 else "Low"
    gap_impact = {s: max(4, min(18, 18 - i * 2)) for i, s in enumerate(missing[:5])}
    verdict_word = "Strong fit" if fit >= 75 else "Good partial fit" if fit >= 45 else "Weak fit"
    role = jd_data.get("role_title", "this role")
    company = jd_data.get("company", "the company")
    return {
        "fit_score": fit,
        "ats_score": ats,
        "matched_skills": matched,
        "missing_skills": missing[:8],
        "resume_suggestions": [
            f"Add JD keywords for {role}: {', '.join((missing or matched)[:3])}.",
            f"Rewrite your summary to target {jd_data.get('role_category', 'this role')} instead of a generic profile.",
            "Add 2-3 measurable achievements that prove the matched skills in this JD.",
        ],
        "skill_gap_impact": gap_impact,
        "one_line_verdict": f"{verdict_word}: matched {len(matched)} of {len(req)} detected role requirements for {role}.",
        "priority": priority,
        "cover_note": f"I am interested in the {role} opportunity at {company}. My background shows strength in {', '.join(matched[:3]) if matched else 'transferable problem-solving and communication'}, and I am ready to close gaps around {', '.join(missing[:2]) if missing else 'the team priorities'} for this role.",
        "role_category": jd_data.get("role_category", "General"),
    }


def _mock(expect_json: bool, agent_type: str = "generic", user_prompt: str = "") -> str:
    """Universal deterministic fallback used when hosted AI/Lemma is unavailable."""
    if not expect_json:
        role = _extract_title(user_prompt, "the role")
        return f"""Hi [Recruiter Name],

I noticed the {role} opening and wanted to reach out. My background includes relevant hands-on work and I would be glad to share how it maps to your team?s needs.

Would you be open to a quick 15-minute conversation this week?

Best,
[Your Name]"""

    resume_text = _section(user_prompt, "RESUME", ["JOB DESCRIPTION", "Return JSON"])
    jd_text = _section(user_prompt, "JOB DESCRIPTION", ["Return JSON"])
    if not jd_text and "JOB DESCRIPTIONS" in user_prompt:
        jd_text = _section(user_prompt, "JOB DESCRIPTIONS", ["Return JSON"])
    if agent_type == "resume":
        data = _offline_resume(_section(user_prompt, "RESUME") or user_prompt)
    elif agent_type == "jd":
        data = _offline_jd(_section(user_prompt, "JOB DESCRIPTION") or user_prompt)
    elif agent_type == "matching":
        jd_data = _offline_jd(jd_text or user_prompt)
        data = _offline_match(resume_text, jd_text or user_prompt, jd_data)
    elif agent_type == "market":
        skills = _keyword_candidates(user_prompt)
        data = {
            "top_skills": [{"skill": s, "frequency": max(25, 90 - i * 6), "importance": "Critical" if i < 3 else "Important"} for i, s in enumerate(skills[:15])],
            "emerging_skills": skills[5:10] or skills[:3],
            "role_summary": "Market demand is based on repeated skills across the pasted job descriptions.",
            "recommended_learning_order": skills[:5],
        }
    elif agent_type == "interview_eval":
        answer = _section(user_prompt, "Candidate Answer") or user_prompt
        star = all(x in answer.lower() for x in ["situation", "task", "action", "result"])
        base = min(9, max(4, len(answer.split()) // 25 + (2 if star else 0)))
        data = {
            "technical_score": base,
            "communication_score": min(10, base + 1),
            "confidence_score": base,
            "overall_score": base,
            "strengths": ["Addresses the question", "Uses relevant context"],
            "improvements": ["Add measurable outcomes", "Structure the answer more clearly with STAR"],
            "ideal_elements": "A strong answer includes context, action, tools used, and measurable result.",
            "overall_feedback": "Useful answer, but it becomes stronger with specific metrics and a clearer structure.",
            "star_used": star,
        }
    elif agent_type == "optimizer":
        jd_skills = _keyword_candidates(user_prompt)
        data = {
            "optimized_summary": f"Role-targeted candidate with strengths in {', '.join(jd_skills[:4]) or 'relevant execution'} and measurable delivery.",
            "optimized_skills_section": jd_skills[:12],
            "missing_keywords": jd_skills[:8],
            "project_suggestions": [f"Create a portfolio project using {s}" for s in jd_skills[:3]],
            "quick_wins": ["Mirror exact JD keywords where truthful", "Add metrics to experience bullets", "Move most relevant skills to the top"],
            "ats_improvements": ["Use standard section headers", "Avoid graphics/tables for key content", "Include exact role title keywords"],
        }
    else:
        data = _offline_match(resume_text, jd_text or user_prompt)
    return json.dumps(data)


def _safe_parse(raw: str, default: dict) -> dict:
    """Parse JSON safely, never crash."""
    try:
        return json.loads(raw)
    except Exception:
        # Try to extract JSON from surrounding text
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        return default


# ══════════════════════════════════════════════════════════════════════════════
# INDIVIDUAL AGENTS — each does exactly one job
# ══════════════════════════════════════════════════════════════════════════════

def resume_agent(resume_text: str) -> dict:
    """Extracts structured candidate profile. Works for ALL roles."""
    raw = _call(
        system="You are a professional resume parser. Extract structured data accurately. Return valid JSON only. No markdown.",
        agent_type="resume",
        user=f"""Parse this resume and return JSON:
{{
  "name": "candidate name or Unknown",
  "current_role": "most recent job title",
  "experience_years": <integer, 0 if fresher>,
  "education": "highest degree and institution",
  "all_skills": [<every skill, tool, language, framework, certification mentioned>],
  "top_skills": [<top 5 strongest based on emphasis and recency>],
  "industry": "<e.g. Technology, Finance, Healthcare, Marketing>",
  "resume_score": <integer 0-100, quality of resume presentation>,
  "summary": "2 sentence professional summary"
}}

RESUME:
{resume_text[:3000]}"""
    )
    result = _safe_parse(raw, {
        "all_skills":[], "top_skills":[], "name":"Candidate",
        "resume_score":50, "industry":"General", "current_role":"",
        "experience_years":0, "summary":""
    })
    # Save to pod
    try:
        from database import FILES_DIR
        import json as j
        (FILES_DIR / "candidate_profile.json").write_text(
            j.dumps(result, indent=2), encoding="utf-8"
        )
    except Exception:
        pass
    return result


def jd_agent(jd_text: str) -> dict:
    """
    Extracts structured requirements from a JD.
    FIXED: Works for ANY role — not just Data Science.
    Role category is auto-detected from content.
    """
    raw = _call(
        system="You are a job description analyst. Extract requirements precisely. Return valid JSON only. No markdown.",
        agent_type="jd",
        user=f"""Analyse this job description and return JSON:
{{
  "company": "<company name, or Unknown if not mentioned>",
  "role_title": "<exact job title>",
  "seniority": "<Fresher/Junior/Mid/Senior/Lead/Manager>",
  "role_category": "<auto-detect the best category, e.g. Data/Analytics, Software Engineering, DevOps/Cloud, QA/Testing, Product Management, Design, Marketing, Sales, Finance, Human Resources, Operations, Customer Success, Legal/Compliance, Healthcare, Education, or General>",
  "required_skills": [<must-have skills, tools, technologies>],
  "nice_to_have_skills": [<optional or preferred skills>],
  "key_responsibilities": [<top 3 main things this role does>],
  "ats_keywords": [<important keywords that ATS systems look for>],
  "industry": "<industry sector e.g. Fintech, EdTech, Healthcare, E-commerce>"
}}

JOB DESCRIPTION:
{jd_text[:2500]}"""
    )
    return _safe_parse(raw, {
        "company":"Unknown", "role_title":"Unknown", "seniority":"Mid",
        "role_category":"General", "required_skills":[], "nice_to_have_skills":[],
        "key_responsibilities":[], "ats_keywords":[], "industry":"General"
    })


def matching_agent(resume_text: str, jd_text: str, jd_data: dict = None) -> dict:
    """
    Core scoring engine.
    FIXED: Role-agnostic — scores any resume vs any JD.
    """
    jd_context = ""
    if jd_data:
        jd_context = f"Role category: {jd_data.get('role_category','')}\nSeniority: {jd_data.get('seniority','')}"

    raw = _call(
        system="You are an expert career coach and ATS specialist. Be accurate and honest. Return valid JSON only. No markdown.",
        agent_type="matching",
        user=f"""Compare this resume against this job description.
{jd_context}

RESUME:
{resume_text[:2500]}

JOB DESCRIPTION:
{jd_text[:2000]}

Return JSON:
{{
  "fit_score": <0-100, how well experience and skills match overall>,
  "ats_score": <0-100, how well resume keywords match JD for ATS systems>,
  "matched_skills": [<skills from JD the candidate demonstrably has>],
  "missing_skills": [<required skills from JD the candidate lacks>],
  "resume_suggestions": [<3 specific, actionable lines to add to resume for this role>],
  "skill_gap_impact": {{<skill_name>: <integer % fit improvement if added>}},
  "one_line_verdict": "<honest one sentence: Strong fit/Good fit/Weak fit + why>",
  "priority": "<High/Medium/Low>",
  "cover_note": "<one paragraph personalised cover note for this specific role>"
}}

Be role-agnostic. Score honestly for the specific JD. Do not assume any default career field."""
    )
    result = _safe_parse(raw, {
        "fit_score":0, "ats_score":0, "matched_skills":[], "missing_skills":[],
        "resume_suggestions":[], "skill_gap_impact":{},
        "one_line_verdict":"Could not analyse", "priority":"Medium", "cover_note":""
    })
    # Calculate opportunity score
    fit  = int(result.get("fit_score", 0))
    ats  = int(result.get("ats_score", 0))
    prio = {"High":100,"Medium":60,"Low":30}.get(result.get("priority","Medium"), 60)
    result["opportunity_score"] = round(fit*0.5 + ats*0.3 + prio*0.2)

    # Always set workflow_action based on fit score
    # (mock may include it, real API may not — always recalculate to be safe)
    if fit >= 75:
        result["workflow_action"] = "IMMEDIATE_APPLY"
    elif fit >= 45:
        result["workflow_action"] = "APPLY_WITH_TAILORING"
    else:
        result["workflow_action"] = "UPSKILL_FIRST"

    # Add role category from JD data
    if jd_data:
        result["role_category"] = jd_data.get("role_category", "General")
    elif not result.get("role_category"):
        result["role_category"] = "General"

    return result


def market_agent(jd_list: list, role_category: str = "General") -> dict:
    """Analyses multiple JDs for skill frequency. Works for any role category."""
    combined = "\n\n---\n\n".join([j[:400] for j in jd_list[:25]])
    raw = _call(
        system="You are a job market analyst. Return valid JSON only. No markdown.",
        agent_type="market",
        user=f"""Analyse these {len(jd_list)} job descriptions for {role_category} roles.

Return JSON:
{{
  "top_skills": [
    {{"skill": "<name>", "frequency": <integer 0-100>, "importance": "<Critical/Important/Nice-to-have>"}},
    ... list top 15 skills with % frequency across all JDs
  ],
  "emerging_skills": [<3-5 skills appearing but growing in demand>],
  "role_summary": "<2 sentence market overview for {role_category}>",
  "recommended_learning_order": [<top 5 skills to learn first for max job matches>]
}}

JOB DESCRIPTIONS:
{combined}"""
    )
    return _safe_parse(raw, {
        "top_skills":[], "emerging_skills":[], "role_summary":"", "recommended_learning_order":[]
    })


def message_agent(company: str, role: str, skills: list, msg_type: str, context: str = "") -> str:
    """Generates personalised recruiter messages for any role."""
    type_desc = {
        "cold_outreach":    "a cold LinkedIn outreach (first contact with recruiter)",
        "follow_up":        "a polite follow-up after applying with no reply for 1 week",
        "referral_request": "a message asking a mutual connection for a referral",
        "thank_you":        "a thank-you note after a screening call",
        "post_interview":   "a post-interview thank-you after a technical/functional round"
    }.get(msg_type, "a professional outreach message")

    skills_str = ", ".join(skills[:3]) if skills else "relevant skills and experience"

    return _call(
        system="You are a career communication expert. Write authentic, human messages. Return only the message text. No explanation.",
        agent_type="message",
        expect_json=False,
        user=f"""Write {type_desc} for a job seeker.

Company: {company}
Role: {role}
Candidate's strongest matching skills: {skills_str}
{f'Context: {context}' if context else ''}

Rules:
- Under 150 words
- Confident, not desperate
- End with a specific question or clear call to action
- Do NOT start with "I hope this message finds you well"
- Do NOT use "I am reaching out to"
- Sound like a real human
- Leave [Recruiter Name] and [Your Name] as placeholders"""
    )


def interview_question_agent(company: str, role: str, missing_skills: list, round_num: int) -> str:
    """Generates role-appropriate interview questions for any job type."""
    q_focus = {
        1: "introductory — ask them to walk you through their background and why they applied",
        2: "technical/functional — test a core skill or knowledge area for this specific role",
        3: f"skill gap probe — ask about their experience with: {', '.join(missing_skills[:2]) if missing_skills else 'a key requirement'}",
        4: "behavioural — STAR format, about a real challenge they faced",
        5: "situational — how would they handle a specific realistic scenario in this role"
    }.get(round_num, "a relevant follow-up question based on this role")

    return _call(
        system=f"You are a senior recruiter at {company} conducting a structured interview for {role}. Be professional and realistic.",
        agent_type="message",
        expect_json=False,
        user=f"Ask one {q_focus} question. Return only the question text. No preamble."
    )


def interview_evaluate_agent(question: str, answer: str, role: str) -> dict:
    """
    Evaluates interview answer across 3 dimensions.
    FIXED: Returns default values if parsing fails, never crashes.
    """
    raw = _call(
        system="You are an experienced hiring manager. Evaluate interview answers honestly and constructively. Return valid JSON only.",
        agent_type="interview_eval",
        user=f"""Role: {role}
Question: {question}
Candidate Answer: {answer}

Evaluate and return JSON:
{{
  "technical_score": <1-10, accuracy and depth for this role>,
  "communication_score": <1-10, clarity and structure>,
  "confidence_score": <1-10, assertiveness and conviction>,
  "overall_score": <1-10, weighted average>,
  "strengths": [<2 specific things they did well>],
  "improvements": [<2 specific things to improve>],
  "ideal_elements": "<what a 9/10 answer would include in 1 sentence>",
  "overall_feedback": "<2-3 sentence honest assessment>",
  "star_used": <true or false>
}}"""
    )
    result = _safe_parse(raw, {
        "technical_score":5, "communication_score":5, "confidence_score":5,
        "overall_score":5, "strengths":["Attempted the question"],
        "improvements":["Add specific examples","Use STAR format"],
        "ideal_elements":"Concrete examples with measurable outcomes",
        "overall_feedback":"Answer needs more structure and specific examples.",
        "star_used": False
    })
    # Ensure overall_score exists
    if not result.get("overall_score"):
        t = result.get("technical_score",5)
        c = result.get("communication_score",5)
        cf = result.get("confidence_score",5)
        result["overall_score"] = round(t*0.5 + c*0.3 + cf*0.2)
    return result


def employability_agent(resume_profile: dict, market_skills: list, analytics: dict) -> dict:
    """
    Calculates employability score with actionable roadmap.
    Formula: resume*0.25 + skill_match*0.35 + market_demand*0.25 + app_success*0.15
    """
    resume_score = int(resume_profile.get("resume_score", 60))
    avg_fit      = int(analytics.get("avg_fit", 0))

    # Skill match
    my_skills    = set(s.lower() for s in resume_profile.get("all_skills", []))
    market_top   = [s["skill"].lower() for s in market_skills[:10]] if market_skills else []
    matched      = sum(1 for s in market_top if any(s in ms or ms in s for ms in my_skills))
    skill_match  = round((matched/len(market_top))*100) if market_top else 50

    market_demand = avg_fit if avg_fit > 0 else skill_match

    total      = analytics.get("total", 0)
    interviews = analytics.get("interview", 0) + analytics.get("offer", 0)
    app_score  = round((interviews/total)*100) if total > 5 else 50

    overall = round(resume_score*0.25 + skill_match*0.35 + market_demand*0.25 + app_score*0.15)

    # Build learning roadmap
    missing_market = [s for s in market_top if not any(s in ms or ms in s for ms in my_skills)]
    top_from_analytics = [s for s,_ in analytics.get("top_missing_skills",[])]
    all_gaps = list(dict.fromkeys(missing_market + top_from_analytics))[:5]
    gap_freq = {s.get("skill","").lower(): s.get("frequency",50) for s in market_skills}

    recommendations = []
    for skill in all_gaps[:4]:
        freq = gap_freq.get(skill, 50)
        impact = round(freq * 0.15)
        weeks  = 2 if impact < 8 else 4 if impact < 12 else 6
        recommendations.append({
            "action":     f"Learn {skill.title()}",
            "impact":     impact,
            "time_weeks": weeks,
            "reason":     f"Appears in ~{freq}% of market job descriptions"
        })

    recommendations.sort(key=lambda x: x["impact"], reverse=True)

    return {
        "overall_score":       overall,
        "resume_score":        resume_score,
        "skill_match_score":   skill_match,
        "market_demand_score": market_demand,
        "application_score":   app_score,
        "top_recommendations": recommendations
    }


def resume_optimizer_agent(resume_text: str, jd_list: list) -> dict:
    """Optimises resume against multiple JDs of ANY role type."""
    combined = "\n".join([j[:300] for j in jd_list[:15]])
    raw = _call(
        system="You are a senior resume writer. Return valid JSON only. No markdown.",
        agent_type="optimizer",
        user=f"""Optimise this resume against {len(jd_list)} job descriptions.

RESUME: {resume_text[:2000]}

JOB DESCRIPTIONS COMBINED: {combined}

Return JSON:
{{
  "optimized_summary": "<2-3 sentence summary hitting most common JD keywords>",
  "optimized_skills_section": [<reordered skills with most market-demanded first>],
  "missing_keywords": [<important keywords from JDs missing from resume>],
  "project_suggestions": [<2-3 project ideas that address the most common skill gaps>],
  "quick_wins": [<3 changes to make today that take under 30 minutes>],
  "ats_improvements": [<2-3 formatting or keyword tips to improve ATS pass rate>]
}}"""
    )
    return _safe_parse(raw, {
        "optimized_summary":"",
        "optimized_skills_section":[],
        "missing_keywords":[],
        "project_suggestions":[],
        "quick_wins":[],
        "ats_improvements":[]
    })


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION AGENT — Lemma-style workflow with conditional routing
# ══════════════════════════════════════════════════════════════════════════════

class OrchestrationAgent:
    """
    Lemma-style workflow orchestrator.
    Chains agents with conditional logic and writes results to pod tables.
    Each workflow step is logged for transparency.

    Workflow pattern (Lemma brief):
    input → state → action → approval point → outcome
    """

    def run_single_analysis(self, resume_text: str, jd_text: str,
                             company: str = "", role: str = "",
                             progress_fn=None) -> dict:
        """Single JD workflow with conditional routing."""
        from database import log_workflow
        start = time.time()

        def step(msg, n, total):
            if progress_fn:
                progress_fn(msg, n, total)

        # Step 1: Extract JD structure
        step("JD Agent: extracting requirements...", 1, 4)
        jd_data = jd_agent(jd_text)

        # Step 2: Match resume vs JD
        step("Matching Agent: scoring resume...", 2, 4)
        match = matching_agent(resume_text, jd_text, jd_data)

        match["company"] = company or jd_data.get("company", "Unknown")
        match["role"]    = role or jd_data.get("role_title", "Unknown")
        match["jd_text"] = jd_text
        match["role_category"] = jd_data.get("role_category", "General")

        fit = int(match.get("fit_score", 0))

        # Step 3: Conditional workflow routing (Lemma pattern: input → state → action)
        step("Orchestrator: routing workflow...", 3, 4)
        if fit >= 75:
            match["workflow_action"]  = "IMMEDIATE_APPLY"
            match["workflow_message"] = (
                f"Strong fit ({fit}%). Apply today. "
                f"Follow-up scheduled in 7 days. "
                f"Use the Message Drafter for your outreach."
            )
        elif fit >= 45:
            match["workflow_action"]  = "APPLY_WITH_TAILORING"
            match["workflow_message"] = (
                f"Good fit ({fit}%). Tailor your resume using the suggestions below, "
                f"then apply. Address skill gaps in your cover note."
            )
        else:
            missing_top = ", ".join(match.get("missing_skills",[])[:3])
            match["workflow_action"]  = "UPSKILL_FIRST"
            match["workflow_message"] = (
                f"Weak fit ({fit}%). Focus on closing these gaps first: {missing_top}. "
                f"Check the Market Intel tab for a learning roadmap."
            )

        step("Done", 4, 4)
        elapsed = round((time.time()-start)*1000)
        log_workflow(
            "single_analysis",
            "success",
            f"{match['company']} — {match['role']} | fit={fit} | action={match['workflow_action']}",
            elapsed
        )
        return match

    def run_bulk_analysis(self, resume_text: str, jd_list: list,
                           progress_fn=None) -> list:
        """
        Bulk JD workflow. Returns ranked priority queue.
        Writes results to pod/tables/applications.json.
        """
        from database import log_workflow
        start   = time.time()
        results = []

        for i, jd in enumerate(jd_list):
            if progress_fn:
                progress_fn(i+1, len(jd_list), f"Analysing JD {i+1} of {len(jd_list)}...")

            jd_data = jd_agent(jd)
            match   = matching_agent(resume_text, jd, jd_data)
            match["company"]       = jd_data.get("company", f"Company {i+1}")
            match["role"]          = jd_data.get("role_title", f"Role {i+1}")
            match["jd_text"]       = jd
            match["role_category"] = jd_data.get("role_category","General")

            fit = int(match.get("fit_score",0))
            match["workflow_action"] = (
                "IMMEDIATE_APPLY" if fit >= 75 else
                "APPLY_WITH_TAILORING" if fit >= 45 else
                "UPSKILL_FIRST"
            )
            results.append(match)

        ranked  = sorted(results, key=lambda x: x.get("opportunity_score",0), reverse=True)
        elapsed = round((time.time()-start)*1000)
        log_workflow(
            "bulk_analysis","success",
            f"{len(jd_list)} JDs | top={ranked[0].get('company','?')} score={ranked[0].get('opportunity_score',0) if ranked else 0}",
            elapsed
        )
        return ranked
