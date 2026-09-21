"""
Recommender

Everything downstream of "we already know the candidate's skills":
    - matching resume skills against known job roles
    - skill-gap analysis for a chosen target role
    - comparing a resume against a pasted job description
    - generating career recommendations
    - a rule-based "AI" resume bullet-point enhancer
"""

import re

from app.utils import (
    get_job_roles,
    get_flat_skill_list,
    get_recommendations_data,
)


def _normalize(*skill_list):
    return {s.strip().lower() for s in skill_list if isinstance(s, str) and s.strip()}


def match_all_roles(resume_skills):
    """
    Compares resume_skills against every role in job_roles.json.

    Returns:
        [{role_id, title, match_percentage, matched_skills, missing_skills}, ...]
    """
    roles = get_job_roles()
    resume_set = _normalize(*resume_skills)
    results = []

    for role_id, role in roles.items():
        required = role["required_skills"]
        required_set = _normalize(*required)
        matched = [s for s in required if s.lower() in resume_set]
        missing = [s for s in required if s.lower() not in resume_set]
        match_pct = (
            round((len(matched) / len(required_set)) * 100)
            if required_set
            else 0
        )

        results.append({
            "role_id": role_id,
            "title": role["title"],
            "match_percentage": match_pct,
            "matched_skills": matched,
            "missing_skills": missing,
        })

    results.sort(key=lambda r: r["match_percentage"], reverse=True)
    return results


def skill_gap_for_role(resume_skills, role_id):
    """Detailed skill-gap breakdown for one specific target role."""
    roles = get_job_roles()
    role = roles.get(role_id)

    if not role:
        return None

    resume_set = _normalize(*resume_skills)
    required = role["required_skills"]
    have = [s for s in required if s.lower() in resume_set]
    missing = [s for s in required if s.lower() not in resume_set]
    fit_score = round((len(have) / len(required)) * 100) if required else 0

    recs_data = get_recommendations_data().get("skill_recommendations", {})
    default_tpl = recs_data.get(
        "default",
        "Practice and build a project using {skill}.",
    )

    missing_with_recs = [
        {
            "skill": skill,
            "recommendation": recs_data.get(skill, default_tpl).format(
                skill=skill
            ),
        }
        for skill in missing
    ]

    return {
        "role_id": role_id,
        "title": role["title"],
        "fit_score": fit_score,
        "have_skills": have,
        "missing_skills": missing_with_recs,
    }


# ---------------------------------------------------------------------
# JD SKILL EXTRACTION
# ---------------------------------------------------------------------
# The role JSON is useful for role matching, but it is NOT a complete
# technology dictionary. A JD can contain technologies that do not belong
# to any of the predefined roles. Therefore JD comparison uses this
# additional taxonomy and then also checks the existing master taxonomy.
#
# IMPORTANT:
# Put longer/specific names before shorter names so that:
# "React.js" is preferred over "React"
# "Node.js" is preferred over "Node"
# ".NET" is preferred over "NET"
JD_SKILL_ALIASES = {
    ".NET": [
        r"\.net",
        r"\.net core",
        r"dotnet",
    ],
    "ASP.NET": [
        r"asp\.net",
        r"aspnet",
    ],
    "Java": [
        r"java",
    ],
    "Python": [
        r"python",
    ],
    "PHP": [
        r"php",
    ],
    "C++": [
        r"c\+\+",
    ],
    "C#": [
        r"c#",
        r"c sharp",
    ],
    "C": [
        r"(?<![+#\w])c(?![+#\w])",
    ],
    "JavaScript": [
        r"javascript",
        r"java script",
    ],
    "TypeScript": [
        r"typescript",
        r"type script",
    ],
    "HTML5": [
        r"html5",
    ],
    "CSS3": [
        r"css3",
    ],
    "React.js": [
        r"react\.js",
        r"reactjs",
    ],
    "React": [
        r"(?<![\w.])react(?![\w.])",
    ],
    "React Native": [
        r"react native",
    ],
    "Node.js": [
        r"node\.js",
        r"nodejs",
    ],
    "Express.js": [
        r"express\.js",
        r"expressjs",
    ],
    "Angular": [
        r"angular",
    ],
    "Django": [
        r"django",
    ],
    "Flask": [
        r"flask",
    ],
    "Spring Boot": [
        r"spring boot",
    ],
    "Android": [
        r"android",
    ],
    "iOS": [
        r"\bios\b",
        r"ios",
    ],
    "Kotlin": [
        r"kotlin",
    ],
    "Swift": [
        r"swift",
    ],
    "Flutter": [
        r"flutter",
    ],
    "SQL": [
        r"(?<!\w)sql(?!\w)",
    ],
    "MySQL": [
        r"mysql",
    ],
    "PostgreSQL": [
        r"postgresql",
        r"postgres",
    ],
    "MongoDB": [
        r"mongodb",
        r"mongo db",
    ],
    "Firebase": [
        r"firebase",
    ],
    "REST APIs": [
        r"rest api",
        r"rest apis",
        r"restful api",
        r"restful apis",
    ],
    "GraphQL": [
        r"graphql",
    ],
    "Git": [
        r"(?<!\w)git(?!\w)",
    ],
    "GitHub": [
        r"github",
    ],
    "Docker": [
        r"docker",
    ],
    "Kubernetes": [
        r"kubernetes",
        r"k8s",
    ],
    "AWS": [
        r"aws",
        r"amazon web services",
    ],
    "Azure": [
        r"azure",
    ],
    "Google Cloud": [
        r"google cloud",
        r"\bgcp\b",
    ],
    "Cloud Technologies": [
        r"cloud technologies",
        r"cloud technology",
        r"cloud computing",
    ],
    "CI/CD": [
        r"ci/cd",
        r"ci cd",
        r"continuous integration",
        r"continuous deployment",
    ],
    "Jenkins": [
        r"jenkins",
    ],
    "Terraform": [
        r"terraform",
    ],
    "Ansible": [
        r"ansible",
    ],
    "Linux": [
        r"linux",
    ],
    "Machine Learning": [
        r"machine learning",
    ],
    "Deep Learning": [
        r"deep learning",
    ],
    "AI / ML": [
        r"ai\s*/\s*ml",
        r"ai\s+/\s+ml",
        r"artificial intelligence\s*(?:and|/)\s*machine learning",
    ],
    "Artificial Intelligence": [
        r"artificial intelligence",
    ],
    "NLP": [
        r"\bnlp\b",
        r"natural language processing",
    ],
    "TensorFlow": [
        r"tensorflow",
    ],
    "PyTorch": [
        r"pytorch",
    ],
    "Pandas": [
        r"pandas",
    ],
    "NumPy": [
        r"numpy",
    ],
    "Scikit-learn": [
        r"scikit[- ]learn",
        r"sklearn",
    ],
    "Statistics": [
        r"statistics",
    ],
    "Data Analysis": [
        r"data analysis",
    ],
    "Data Visualization": [
        r"data visualization",
    ],
    "Power BI": [
        r"power bi",
    ],
    "Tableau": [
        r"tableau",
    ],
    "Excel": [
        r"(?<!\w)excel(?!\w)",
    ],
    "D365 MS Dynamics": [
        r"d365\s*ms\s*dynamics",
        r"d365",
        r"microsoft dynamics 365",
        r"ms dynamics",
    ],
    "MERN Stack": [
        r"mern stack",
        r"\bmern\b",
    ],
    "MEAN Stack": [
        r"mean stack",
        r"\bmean\b",
    ],
    "Microservices": [
        r"microservices",
        r"microservices architecture",
    ],
    "System Design": [
        r"system design",
    ],
    "OOP": [
        r"object[- ]oriented programming",
        r"\boop\b",
    ],
    "Data Structures": [
        r"data structures",
    ],
    "Algorithms": [
        r"algorithms",
    ],
}


def _skill_pattern(pattern):
    """Compile a safe word-aware regex for a skill alias."""
    return re.compile(pattern, re.IGNORECASE)


def _extract_jd_skills(jd_text):
    """
    Extract all recognizable technical skills from JD text.

    This does not depend only on job_roles.json. It combines the existing
    master taxonomy with additional JD-specific technology aliases so that
    skills such as Android, iOS, D365 MS Dynamics, Cloud Technologies,
    AI / ML and MERN Stack are not lost.
    """
    if not jd_text:
        return []

    text = re.sub(r"\s+", " ", jd_text).strip()
    found = []

    # First check the extended taxonomy.
    for canonical, aliases in JD_SKILL_ALIASES.items():
        for alias in aliases:
            if _skill_pattern(alias).search(text):
                found.append(canonical)
                break

    # Then check any skills already present in the application's master
    # taxonomy. This keeps the function compatible with future additions
    # to job_roles.json / the existing skill taxonomy.
    try:
        master_skills = get_flat_skill_list()
    except Exception:
        master_skills = []

    existing_normalized = {skill.lower(): skill for skill in found}

    for skill in sorted(master_skills, key=len, reverse=True):
        if not isinstance(skill, str) or not skill.strip():
            continue

        pattern = (
            r"(?<!\w)"
            + re.escape(skill.strip()).replace(r"\ ", r"\s+")
            + r"(?!\w)"
        )

        if re.search(pattern, text, re.IGNORECASE):
            key = skill.strip().lower()
            if key not in existing_normalized:
                found.append(skill.strip())
                existing_normalized[key] = skill.strip()

    # Remove duplicates while preserving detection order.
    unique = []
    seen = set()

    for skill in found:
        key = skill.lower()
        if key not in seen:
            seen.add(key)
            unique.append(skill)

    return unique


def _skill_sets_match(resume_skill, jd_skill):
    """
    Handles common equivalent names between resume and JD skills.
    """
    resume_key = resume_skill.strip().lower()
    jd_key = jd_skill.strip().lower()

    aliases = {
        ".net": {".net", "dotnet", "asp.net"},
        "react.js": {"react.js", "reactjs", "react"},
        "react": {"react.js", "reactjs", "react"},
        "node.js": {"node.js", "nodejs", "node"},
        "express.js": {"express.js", "expressjs", "express"},
        "ai / ml": {
            "ai / ml",
            "artificial intelligence",
            "machine learning",
            "ai",
            "ml",
        },
        "artificial intelligence": {
            "ai / ml",
            "artificial intelligence",
            "ai",
        },
        "machine learning": {
            "ai / ml",
            "machine learning",
            "ml",
        },
        "ios": {"ios", "iOS".lower()},
        "d365 ms dynamics": {
            "d365 ms dynamics",
            "d365",
            "microsoft dynamics 365",
            "ms dynamics",
        },
    }

    resume_variants = aliases.get(resume_key, {resume_key})
    jd_variants = aliases.get(jd_key, {jd_key})

    return bool(resume_variants.intersection(jd_variants))


def compare_resume_with_jd(resume_skills, jd_text):
    """
    Extracts skills from a job description and compares them with
    resume_skills.

    Returns:
        jd_skills
        matched_skills
        missing_skills
        match_score
    """
    jd_skills = _extract_jd_skills(jd_text)
    resume_skills_clean = [
        skill.strip()
        for skill in resume_skills
        if isinstance(skill, str) and skill.strip()
    ]

    matched = []
    missing = []

    for jd_skill in jd_skills:
        if any(
            _skill_sets_match(resume_skill, jd_skill)
            for resume_skill in resume_skills_clean
        ):
            matched.append(jd_skill)
        else:
            missing.append(jd_skill)

    match_score = (
        round((len(matched) / len(jd_skills)) * 100)
        if jd_skills
        else 0
    )

    return {
        "jd_skills": jd_skills,
        "matched_skills": matched,
        "missing_skills": missing,
        "match_score": match_score,
    }


def generate_career_recommendations(resume_skills, top_n=3):
    """
    Returns the top N best-fit roles as career recommendations, each
    with a short human-readable recommendation string.
    """
    ranked = match_all_roles(resume_skills)
    top_roles = ranked[:top_n]
    recommendations = []

    for role in top_roles:
        if role["missing_skills"]:
            gap_note = (
                f"Focus next on {', '.join(role['missing_skills'][:3])} "
                "to strengthen this fit."
            )
        else:
            gap_note = (
                "Your current skill set already covers this role's "
                "core requirements well."
            )

        recommendations.append({
            "career_title": role["title"],
            "match_percentage": role["match_percentage"],
            "recommendation": gap_note,
        })

    return recommendations


# =====================================================================
# RESUME BULLET-POINT ENHANCER
# =====================================================================

WEAK_STARTERS = {
    "worked on": "Delivered",
    "responsible for": "Owned",
    "helped": "Contributed to",
    "did": "Executed",
    "made": "Built",
    "used": "Leveraged",
    "built": "Engineered",
    "created": "Designed and developed",
}


def enhance_bullet_point(original_text):
    """
    Rule-based enhancement of a single resume bullet point:
        1. Detect technologies mentioned from the skills taxonomy.
        2. Replace a weak opening verb with a stronger action verb.
        3. If the sentence has no quantified impact, append a plausible
           impact phrase clearly framed as a suggestion to customize.
    """
    original = original_text.strip()

    if not original:
        return {"original": original, "enhanced": ""}

    rec_data = get_recommendations_data()
    action_verbs = rec_data.get("action_verbs", ["Improved"])
    impact_phrases = rec_data.get(
        "impact_phrases",
        ["improving overall efficiency"],
    )

    text = original
    lower = text.lower()
    replaced = False

    for weak, strong in WEAK_STARTERS.items():
        if lower.startswith(weak):
            text = strong + text[len(weak):]
            replaced = True
            break

    if not replaced:
        verb = action_verbs[len(text) % len(action_verbs)]
        first_word = text.split(" ", 1)[0]

        if (
            not first_word.endswith("ed")
            and not first_word.endswith("ing")
        ):
            text = (
                f"{verb} {text[0].lower()}{text[1:]}"
                if text
                else text
            )

    has_number = bool(re.search(r"\d", text))

    if not has_number:
        phrase = impact_phrases[len(original) % len(impact_phrases)]
        text = text.rstrip(". ") + f", {phrase}."
    elif not text.endswith("."):
        text += "."

    return {
        "original": original,
        "enhanced": text,
    }
