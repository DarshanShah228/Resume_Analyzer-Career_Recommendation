"""
ResumeAnalyzer
==============
Lightweight, dependency-free (no spaCy/NLTK) resume analysis engine.
Uses keyword/regex matching against the skills taxonomy in data/skills.json
to extract skills, estimate experience, detect education, and compute a
set of explainable sub-scores that mirror the metric cards already
present in the resume-analysis.html template (ATS Format, Skill
Extraction, Impact, Keywords) plus an overall resume score.
"""

import re
from app.utils import get_skills_taxonomy


EDUCATION_KEYWORDS = [
    "B.Tech", "B.E", "BE ", "Bachelor of Technology", "Bachelor of Engineering",
    "M.Tech", "M.E", "Master of Technology", "MCA", "BCA", "B.Sc", "M.Sc",
    "Bachelor of Science", "Master of Science", "Bachelor of Computer Applications",
    "Master of Computer Applications", "PhD", "Ph.D", "Diploma", "University",
    "College", "Institute of Technology", "B.Com", "MBA"
]

SECTION_HEADERS = [
    "experience", "education", "skills", "projects", "certification",
    "objective", "summary", "achievements", "contact"
]

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"(\+?\d{1,3}[-.\s]?)?\d{10}")
YEARS_EXP_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*year[s]?", re.IGNORECASE)
QUANTIFIED_REGEX = re.compile(r"\d+(\.\d+)?\s*%|\$\d+|\b\d{2,}\+?\b")
DATE_RANGE_REGEX = re.compile(
    r"(20\d{2}|19\d{2})\s*(-|to|–)\s*(20\d{2}|present|current)",
    re.IGNORECASE
)


class ResumeAnalyzer:
    """Runs the full analysis pipeline over raw extracted resume text."""

    def __init__(self, text):
        self.text = text or ""
        self.lower_text = self.text.lower()
        self.taxonomy = get_skills_taxonomy()

    # ---------------------------------------------------------------
    # SKILLS
    # ---------------------------------------------------------------
    def extract_skills(self):
        """
        Returns dict: { category: [matched skills] } based on
        case-insensitive whole-word/phrase matching against skills.json.
        """
        found_by_category = {}

        for category, skills in self.taxonomy.items():
            matches = []
            for skill in skills:
                pattern = r"(?<!\w)" + re.escape(skill).replace(r"\ ", r"\s+") + r"(?!\w)"
                if re.search(pattern, self.text, re.IGNORECASE):
                    matches.append(skill)
            if matches:
                found_by_category[category] = matches

        return found_by_category

    def flat_skills(self, skills_by_category=None):
        skills_by_category = skills_by_category or self.extract_skills()
        flat = []
        for skills in skills_by_category.values():
            flat.extend(skills)
        return flat

    # ---------------------------------------------------------------
    # EXPERIENCE
    # ---------------------------------------------------------------
    def estimate_experience(self):
        """
        Best-effort estimate of years of experience:
        1) look for explicit "X years" mentions
        2) fall back to widest date range span found in the text
        Returns a dict with a human-readable summary + numeric years.
        """
        explicit_matches = [float(m) for m in YEARS_EXP_REGEX.findall(self.text)]
        if explicit_matches:
            years = max(explicit_matches)
            return {"years": years, "summary": f"~{years:g} years (stated in resume)"}

        date_ranges = DATE_RANGE_REGEX.findall(self.text)
        if date_ranges:
            start_years = [int(m[0]) for m in date_ranges]
            end_years = [
                2024 if m[2].lower() in ("present", "current") else int(m[2])
                for m in date_ranges
            ]
            span = max(end_years) - min(start_years)
            span = max(span, 0)
            return {"years": span, "summary": f"~{span} years (estimated from dates)"}

        return {"years": 0, "summary": "Fresher / not clearly stated"}

    # ---------------------------------------------------------------
    # EDUCATION
    # ---------------------------------------------------------------
    def extract_education(self):
        found = []
        for keyword in EDUCATION_KEYWORDS:
            if keyword.lower() in self.lower_text:
                found.append(keyword.strip())
        # de-duplicate while preserving order
        seen = set()
        unique = []
        for item in found:
            if item.lower() not in seen:
                seen.add(item.lower())
                unique.append(item)
        return unique

    # ---------------------------------------------------------------
    # SCORING
    # ---------------------------------------------------------------
    def score_ats_format(self):
        """Checks for standard resume hygiene: sections, contact info, length."""
        score = 0

        sections_found = sum(1 for h in SECTION_HEADERS if h in self.lower_text)
        score += min(sections_found, 6) * 8          # up to 48

        if EMAIL_REGEX.search(self.text):
            score += 15
        if PHONE_REGEX.search(self.text):
            score += 12

        word_count = len(self.text.split())
        if 250 <= word_count <= 1200:
            score += 25
        elif word_count > 0:
            score += 10

        return min(round(score), 100)

    def score_skill_extraction(self, flat_skills):
        """Rewards breadth of recognized skills found in the resume."""
        count = len(flat_skills)
        score = min(count * 6, 100)
        return score

    def score_impact(self):
        """Rewards quantified, achievement-oriented bullet points."""
        quantified_hits = len(QUANTIFIED_REGEX.findall(self.text))
        action_verb_hits = sum(
            1 for v in [
                "led", "built", "developed", "designed", "improved",
                "optimized", "created", "implemented", "managed", "automated"
            ] if v in self.lower_text
        )
        score = min(quantified_hits * 8 + action_verb_hits * 5, 100)
        return score

    def score_keywords(self, flat_skills):
        """
        Rough proxy for ATS keyword density: recognized skill mentions
        relative to total word count.
        """
        word_count = max(len(self.text.split()), 1)
        density = (len(flat_skills) / word_count) * 100
        score = min(round(density * 12), 100)
        return score

    # ---------------------------------------------------------------
    # STRENGTHS / IMPROVEMENTS (simple heuristics for feedback text)
    # ---------------------------------------------------------------
    def build_strengths_and_improvements(self, sub_scores, flat_skills, education):
        strengths = []
        improvements = []

        if sub_scores["ats_format"] >= 70:
            strengths.append("Resume follows a clean, ATS-friendly structure with clear sections.")
        else:
            improvements.append("Add clear section headers (Experience, Education, Skills, Projects).")

        if len(flat_skills) >= 8:
            strengths.append(f"Strong, diverse skill set detected ({len(flat_skills)} recognized skills).")
        else:
            improvements.append("List more relevant technical skills explicitly (avoid only mentioning them in prose).")

        if sub_scores["impact"] >= 60:
            strengths.append("Good use of measurable, quantified achievements in bullet points.")
        else:
            improvements.append("Quantify achievements with numbers/percentages (e.g. 'reduced load time by 30%').")

        if education:
            strengths.append(f"Education clearly stated ({education[0]}).")
        else:
            improvements.append("Make your education/degree explicit and easy to find.")

        if EMAIL_REGEX.search(self.text) and PHONE_REGEX.search(self.text):
            strengths.append("Contact information (email & phone) is present and easy to find.")
        else:
            improvements.append("Include a clear email and phone number near the top of the resume.")

        return strengths[:4], improvements[:4]

    # ---------------------------------------------------------------
    # PUBLIC ENTRY POINT
    # ---------------------------------------------------------------
    def analyze(self):
        skills_by_category = self.extract_skills()
        flat_skills = self.flat_skills(skills_by_category)
        experience = self.estimate_experience()
        education = self.extract_education()

        sub_scores = {
            "ats_format": self.score_ats_format(),
            "skill_extraction": self.score_skill_extraction(flat_skills),
            "impact": self.score_impact(),
            "keywords": self.score_keywords(flat_skills),
        }

        overall_score = round(
            sub_scores["ats_format"] * 0.25 +
            sub_scores["skill_extraction"] * 0.30 +
            sub_scores["impact"] * 0.25 +
            sub_scores["keywords"] * 0.20
        )

        strengths, improvements = self.build_strengths_and_improvements(
            sub_scores, flat_skills, education
        )

        return {
            "overall_score": overall_score,
            "sub_scores": sub_scores,
            "skills_by_category": skills_by_category,
            "flat_skills": flat_skills,
            "experience": experience,
            "education": education,
            "strengths": strengths,
            "improvements": improvements,
        }
