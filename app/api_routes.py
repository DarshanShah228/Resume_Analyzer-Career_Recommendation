import json
import re
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db, bcrypt
from app.models import (
    Resume,
    ResumeAnalysis,
    SkillGap,
    JobDescription,
    JDComparison,
    CareerRecommendation,
    User,
)
from app.utils import (
    allowed_file,
    save_resume_file,
    extract_text_from_file,
)
from app.analyzer import ResumeAnalyzer
from app.recommender import (
    match_all_roles,
    skill_gap_for_role,
    compare_resume_with_jd,
    generate_career_recommendations,
    enhance_bullet_point,
)
from app.utils import get_job_roles
api = Blueprint("api", __name__, url_prefix="/api")
# =====================================================================
# HELPERS
# =====================================================================
def _latest_resume():
    return (
        Resume.query
        .filter_by(user_id=current_user.id)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )
def _error(message, status=400):
    return jsonify({"error": message}), status
def _extract_candidate_name(text):
    """
    Extract the candidate/person name from the beginning of the
    uploaded resume text.
    The logged-in user's name is NOT used here.
    """
    if not text:
        return None
    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
    ]
    lines = [line for line in lines if line]
    if not lines:
        return None
    ignored_exact = {
        "resume",
        "cv",
        "curriculum vitae",
        "curriculum-vitae",
        "curriculum_vitae",
        "profile",
        "professional profile",
        "resume profile",
        "personal details",
        "contact details",
    }
    ignored_words = {
        "resume",
        "curriculum",
        "vitae",
        "profile",
        "objective",
        "summary",
        "experience",
        "education",
        "skills",
        "projects",
        "certifications",
        "contact",
        "email",
        "phone",
        "mobile",
        "address",
        "linkedin",
        "github",
        "developer",
        "engineer",
        "analyst",
        "designer",
        "student",
        "software",
    }
    email_pattern = re.compile(
        r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$",
        re.IGNORECASE,
    )
    phone_pattern = re.compile(
        r"^[+()\d\s\-]{7,}$"
    )
    url_pattern = re.compile(
        r"^(https?://|www\.|linkedin\.com|github\.com)",
        re.IGNORECASE,
    )
    name_pattern = re.compile(
        r"^[A-Za-z][A-Za-z.'-]*(?:\s+[A-Za-z][A-Za-z.'-]*){1,4}$"
    )
    candidates = []
    for index, line in enumerate(lines[:30]):
        normalized = line.lower().strip()
        if normalized in ignored_exact:
            continue
        if email_pattern.match(line):
            continue
        if phone_pattern.match(line):
            continue
        if url_pattern.match(line):
            continue
        if any(char.isdigit() for char in line):
            continue
        words = line.split()
        if len(words) < 2 or len(words) > 5:
            continue
        if not name_pattern.match(line):
            continue
        lower_words = {word.lower().strip(".,") for word in words}
        if lower_words.intersection(ignored_words):
            continue
        score = 0
        # Names are usually near the top of a resume.
        score += max(0, 20 - index)
        # Two or three words are very common for personal names.
        if 2 <= len(words) <= 3:
            score += 10
        # Proper-name capitalization is a useful signal.
        if all(
            word[0].isupper()
            for word in words
            if word
        ):
            score += 10
        candidates.append((score, line))
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )
    return candidates[0][1]
def _resume_summary_json(resume):
    """
    Serialize a Resume + its ResumeAnalysis for the frontend.
    """
    analysis = resume.analysis
    if not analysis:
        return {
            "resume_id": resume.id,
            "file_name": resume.file_name,
            "uploaded_at": resume.uploaded_at.isoformat(),
            "analyzed": False,
            "candidate_name": _extract_candidate_name(
                resume.extracted_text
            ),
        }
    analysis_result = json.loads(
        analysis.analysis_result or "{}"
    )
    candidate_name = analysis_result.get(
        "candidate_name"
    )
    if not candidate_name:
        candidate_name = _extract_candidate_name(
            resume.extracted_text
        )
    return {
        "resume_id": resume.id,
        "file_name": resume.file_name,
        "uploaded_at": resume.uploaded_at.isoformat(),
        "analyzed": True,
        "candidate_name": candidate_name,
        "overall_score": analysis.resume_score,
        "sub_scores": analysis_result.get(
            "sub_scores",
            {},
        ),
        "skills_by_category": analysis_result.get(
            "skills_by_category",
            {},
        ),
        "flat_skills": json.loads(
            analysis.skills or "[]"
        ),
        "experience": json.loads(
            analysis.experience or "{}"
        ),
        "education": json.loads(
            analysis.education or "[]"
        ),
        "strengths": analysis_result.get(
            "strengths",
            [],
        ),
        "improvements": analysis_result.get(
            "improvements",
            [],
        ),
        "analyzed_at": analysis.analyzed_at.isoformat(),
    }
# =====================================================================
# RESUME UPLOAD & ANALYSIS
# =====================================================================
@api.route("/resume/upload", methods=["POST"])
@login_required
def upload_resume_api():
    if "file" not in request.files:
        return _error(
            "No file part in the request."
        )
    file_storage = request.files["file"]
    if file_storage.filename == "":
        return _error(
            "No file selected."
        )
    if not allowed_file(file_storage.filename):
        return _error(
            "Unsupported file type. "
            "Please upload a PDF, DOCX, DOC, or TXT file."
        )
    original_name, stored_name, absolute_path = (
        save_resume_file(
            file_storage,
            current_user.id,
        )
    )
    ext = stored_name.rsplit(
        ".",
        1,
    )[1].lower()
    extracted_text = extract_text_from_file(
        absolute_path,
        ext,
    )
    if not extracted_text.strip():
        return _error(
            "Could not extract any text from this file. "
            "Try a different file, or a text-based "
            "(not scanned/image) PDF.",
            422,
        )
    resume = Resume(
        user_id=current_user.id,
        file_name=original_name,
        file_path=absolute_path,
        extracted_text=extracted_text,
    )
    db.session.add(resume)
    db.session.flush()
    # ---------------------------------------------------------------
    # Extract candidate name from the uploaded resume itself.
    # ---------------------------------------------------------------
    candidate_name = _extract_candidate_name(
        extracted_text
    )
    # ---------------------------------------------------------------
    # Run resume analyzer.
    # ---------------------------------------------------------------
    result = ResumeAnalyzer(
        extracted_text
    ).analyze()
    analysis = ResumeAnalysis(
        resume_id=resume.id,
        resume_score=result["overall_score"],
        skills=json.dumps(
            result["flat_skills"]
        ),
        experience=json.dumps(
            result["experience"]
        ),
        education=json.dumps(
            result["education"]
        ),
        analysis_result=json.dumps({
            "candidate_name": candidate_name,
            "sub_scores": result["sub_scores"],
            "skills_by_category": result[
                "skills_by_category"
            ],
            "strengths": result["strengths"],
            "improvements": result[
                "improvements"
            ],
        }),
    )
    db.session.add(analysis)
    # ---------------------------------------------------------------
    # Persist top-3 career recommendations.
    # ---------------------------------------------------------------
    recs = generate_career_recommendations(
        result["flat_skills"],
        top_n=3,
    )
    for rec in recs:
        db.session.add(
            CareerRecommendation(
                resume_id=resume.id,
                career_title=rec[
                    "career_title"
                ],
                match_percentage=rec[
                    "match_percentage"
                ],
                recommendation=rec[
                    "recommendation"
                ],
            )
        )
    db.session.commit()
    return jsonify({
        "message": "Resume analyzed successfully.",
        "resume_id": resume.id,
        "file_name": original_name,
        "candidate_name": candidate_name,
        "overall_score": result[
            "overall_score"
        ],
    })
@api.route("/resume/latest", methods=["GET"])
@login_required
def latest_resume_api():
    resume = _latest_resume()
    if not resume:
        return jsonify({
            "resume": None
        })
    return jsonify({
        "resume": _resume_summary_json(
            resume
        )
    })
# =====================================================================
# ROLES / SKILL GAP
# =====================================================================
@api.route("/roles", methods=["GET"])
@login_required
def roles_api():
    roles = get_job_roles()
    role_list = [
        {
            "role_id": role_id,
            "title": role["title"],
        }
        for role_id, role in roles.items()
    ]
    return jsonify({
        "roles": role_list
    })
@api.route("/skill-gap", methods=["GET"])
@login_required
def skill_gap_api():
    resume = _latest_resume()
    if not resume or not resume.analysis:
        return _error(
            "Please upload and analyze a resume first.",
            404,
        )
    resume_skills = json.loads(
        resume.analysis.skills or "[]"
    )
    ranked_roles = match_all_roles(
        resume_skills
    )
    role_id = request.args.get(
        "role_id"
    )
    if not role_id and ranked_roles:
        role_id = ranked_roles[0]["role_id"]
    gap = (
        skill_gap_for_role(
            resume_skills,
            role_id,
        )
        if role_id
        else None
    )
    if not gap:
        return _error(
            "Unknown target role.",
            404,
        )
    SkillGap.query.filter_by(
        resume_id=resume.id
    ).delete()
    for item in gap["missing_skills"]:
        db.session.add(
            SkillGap(
                resume_id=resume.id,
                skill_name=item["skill"],
                skill_level="missing",
                recommendation=item[
                    "recommendation"
                ],
            )
        )
    db.session.commit()
    return jsonify({
        "target_role": gap,
        "all_roles": [
            {
                "role_id": role["role_id"],
                "title": role["title"],
                "match_percentage": role[
                    "match_percentage"
                ],
            }
            for role in ranked_roles
        ],
    })
@api.route(
    "/career-recommendations",
    methods=["GET"],
)
@login_required
def career_recommendations_api():
    resume = _latest_resume()
    if not resume or not resume.analysis:
        return _error(
            "Please upload and analyze a resume first.",
            404,
        )
    resume_skills = json.loads(
        resume.analysis.skills or "[]"
    )
    recommendations = (
        generate_career_recommendations(
            resume_skills,
            top_n=5,
        )
    )
    return jsonify({
        "recommendations": recommendations
    })
# =====================================================================
# JOB DESCRIPTION COMPARISON
# =====================================================================
@api.route(
    "/compare-jd",
    methods=["POST"],
)
@login_required
def compare_jd_api():

    resume = _latest_resume()

    if not resume or not resume.analysis:
        return _error(
            "Please upload and analyze a resume first.",
            404,
        )

    # ============================================================
    # MODE 1: JD PDF UPLOAD
    # ============================================================

    jd_file = request.files.get("jd_file")

    if jd_file:

        if jd_file.filename == "":
            return _error(
                "Please select a JD PDF."
            )

        if not jd_file.filename.lower().endswith(".pdf"):
            return _error(
                "Only PDF files are accepted."
            )

        try:
            import io
            from pypdf import PdfReader

            reader = PdfReader(
                io.BytesIO(
                    jd_file.read()
                )
            )

            extracted_pages = []

            for page in reader.pages:

                text = page.extract_text()

                if text:
                    extracted_pages.append(
                        text
                    )

            jd_text = "\n".join(
                extracted_pages
            ).strip()

        except Exception as exc:

            return _error(
                f"Could not read the JD PDF: {exc}",
                422,
            )

        if not jd_text:

            return _error(
                "Could not extract text from the JD PDF. Please use a text-based PDF."
            )

        # --------------------------------------------------------
        # Try to extract job title from PDF text
        # --------------------------------------------------------

        lines = [
            line.strip()
            for line in jd_text.splitlines()
            if line.strip()
        ]

        job_title = ""

        # Look for common title labels first
        title_labels = [
            "job title",
            "position",
            "role",
            "designation",
        ]

        for line in lines[:30]:

            lower_line = line.lower()

            for label in title_labels:

                if lower_line.startswith(
                    label + ":"
                ):

                    job_title = line.split(
                        ":",
                        1
                    )[1].strip()

                    break

            if job_title:
                break

        # --------------------------------------------------------
        # Fallback: use first meaningful line
        # --------------------------------------------------------

        if not job_title and lines:

            ignored = {
                "job description",
                "about us",
                "requirements",
                "responsibilities",
                "qualifications",
                "skills",
            }

            for line in lines[:15]:

                if (
                    len(line) >= 3
                    and len(line) <= 120
                    and line.lower()
                    not in ignored
                ):

                    job_title = line

                    break

        if not job_title:

            job_title = "Uploaded Job Description"


    # ============================================================
    # MODE 2: MANUAL JD
    # ============================================================

    else:

        payload = (
            request.get_json(
                silent=True
            )
            or request.form
        )

        job_title = (
            payload.get(
                "target_job_title"
            )
            or ""
        ).strip()

        jd_text = (
            payload.get(
                "job_description"
            )
            or ""
        ).strip()

        # Manual mode requires BOTH
        if not job_title:

            return _error(
                "Please enter the job title."
            )

        if not jd_text:

            return _error(
                "Please enter the job description."
            )

        if len(jd_text) < 30:

            return _error(
                "Please provide a more complete job description."
            )


    # ============================================================
    # COMPARE RESUME WITH JD
    # ============================================================

    resume_skills = json.loads(
        resume.analysis.skills
        or "[]"
    )

    result = compare_resume_with_jd(
        resume_skills,
        jd_text,
    )


    # ============================================================
    # SAVE JOB DESCRIPTION
    # ============================================================

    job_description = JobDescription(
        user_id=current_user.id,
        job_title=job_title,
        description=jd_text,
    )

    db.session.add(
        job_description
    )

    db.session.flush()


    # ============================================================
    # SAVE COMPARISON
    # ============================================================

    comparison = JDComparison(
        resume_id=resume.id,
        job_description_id=job_description.id,
        match_score=result[
            "match_score"
        ],
        matched_skills=json.dumps(
            result[
                "matched_skills"
            ]
        ),
        missing_skills=json.dumps(
            result[
                "missing_skills"
            ]
        ),
    )

    db.session.add(
        comparison
    )

    db.session.commit()


    # ============================================================
    # RESPONSE
    # ============================================================

    return jsonify({

        "comparison_id":
            comparison.id,

        "job_title":
            job_title,

        "match_score":
            result[
                "match_score"
            ],

        "matched_skills":
            result[
                "matched_skills"
            ],

        "missing_skills":
            result[
                "missing_skills"
            ],

        "jd_skills":
            result[
                "jd_skills"
            ],

    })

@api.route("/jd-results/latest", methods=["GET"])
@login_required
def jd_results_latest_api():
    resume = _latest_resume()

    if not resume:
        return jsonify({"comparison": None})

    comparison = (
        JDComparison.query
        .filter_by(resume_id=resume.id)
        .order_by(JDComparison.compared_at.desc())
        .first()
    )

    if not comparison:
        return jsonify({"comparison": None})

    job_description = JobDescription.query.get(
        comparison.job_description_id
    )

    try:
        resume_skills = json.loads(
            resume.analysis.skills or "[]"
        )
    except (TypeError, ValueError):
        resume_skills = []

    try:
        matched_skills = json.loads(
            comparison.matched_skills or "[]"
        )
    except (TypeError, ValueError):
        matched_skills = []

    try:
        missing_skills = json.loads(
            comparison.missing_skills or "[]"
        )
    except (TypeError, ValueError):
        missing_skills = []

    jd_skills = list(
        dict.fromkeys(
            matched_skills + missing_skills
        )
    )

    return jsonify({
        "comparison": {
            "comparison_id": comparison.id,
            "job_title": (
                job_description.job_title
                if job_description
                else ""
            ),
            "resume_name": resume.file_name,
            "resume_skills": resume_skills,
            "jd_skills": jd_skills,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "match_score": comparison.match_score,
            "compared_at": comparison.compared_at.isoformat(),
            "jd_source": "Uploaded JD PDF"
        }
    })
# =====================================================================
# AI BULLET-POINT ENHANCER
# =====================================================================
@api.route(
    "/enhance-bullet",
    methods=["POST"],
)
@login_required
def enhance_bullet_api():
    payload = (
        request.get_json(silent=True)
        or {}
    )
    text = (
        payload.get("text")
        or ""
    ).strip()
    if not text:
        return _error(
            "Please provide bullet point text to enhance."
        )
    result = enhance_bullet_point(text)
    return jsonify(result)
# =====================================================================
# DASHBOARD SUMMARY
# =====================================================================
@api.route(
    "/dashboard-summary",
    methods=["GET"],
)
@login_required
def dashboard_summary_api():
    resumes = (
        Resume.query
        .filter_by(
            user_id=current_user.id
        )
        .order_by(
            Resume.uploaded_at.desc()
        )
        .all()
    )
    resume_count = len(resumes)
    latest = (
        resumes[0]
        if resumes
        else None
    )
    latest_score = None
    best_role = None
    if latest and latest.analysis:
        latest_score = (
            latest.analysis.resume_score
        )
        resume_skills = json.loads(
            latest.analysis.skills
            or "[]"
        )
        ranked = match_all_roles(
            resume_skills
        )
        if ranked:
            best_role = {
                "title": ranked[0]["title"],
                "match_percentage": ranked[0][
                    "match_percentage"
                ],
            }
    comparisons_count = 0
    if latest:
        comparisons_count = (
            JDComparison.query
            .filter_by(
                resume_id=latest.id
            )
            .count()
        )
    return jsonify({
        "user_name": current_user.name,
        "resume_count": resume_count,
        "latest_resume": {
            "file_name": latest.file_name,
            "uploaded_at": latest.uploaded_at.isoformat(),
        } if latest else None,
        "latest_score": latest_score,
        "best_role_match": best_role,
        "jd_comparisons_count": comparisons_count,
    })

# =====================================================================
# ADMIN USER MANAGEMENT
# =====================================================================

def _admin_required():
    if not current_user.is_authenticated or current_user.role != "admin":
        return jsonify({"error": "Administrator access required."}), 403
    return None


def _user_json(user):
    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@api.route("/admin/users", methods=["GET"])
@login_required
def admin_users_api():
    access_error = _admin_required()
    if access_error:
        return access_error

    users = User.query.order_by(
        User.created_at.desc(),
        User.id.desc()
    ).all()

    now = datetime.utcnow()
    today = now.date()
    week_start = now - timedelta(days=7)
    month_start = now.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    total = len(users)
    admins = sum(1 for user in users if user.role == "admin")
    regular = sum(1 for user in users if user.role == "user")

    signed_up_today = sum(
        1 for user in users
        if user.created_at and user.created_at.date() == today
    )
    signed_up_this_week = sum(
        1 for user in users
        if user.created_at and user.created_at >= week_start
    )
    signed_up_this_month = sum(
        1 for user in users
        if user.created_at and user.created_at >= month_start
    )

    return jsonify({
        "users": [_user_json(user) for user in users],
        "stats": {
            "total": total,
            "admins": admins,
            "regular": regular,
            "signed_up_today": signed_up_today,
            "signed_up_this_week": signed_up_this_week,
            "signed_up_this_month": signed_up_this_month,
            "admin_percentage": round((admins / total) * 100) if total else 0,
            "regular_percentage": round((regular / total) * 100) if total else 0,
        },
    })


@api.route("/admin/users", methods=["POST"])
@login_required
def admin_create_user_api():
    access_error = _admin_required()
    if access_error:
        return access_error

    payload = request.get_json(silent=True) or {}

    name = str(payload.get("name", "")).strip()
    username = str(payload.get("username", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    role = str(payload.get("role", "user")).strip().lower()

    if not name or not username or not email or not password:
        return _error("Name, username, email, and password are required.")

    if role not in {"user", "admin"}:
        return _error("Invalid user role.")

    if len(password) < 6:
        return _error("Password must contain at least 6 characters.")

    if User.query.filter_by(username=username).first():
        return _error("Username already exists.", 409)

    if User.query.filter_by(email=email).first():
        return _error("Email already exists.", 409)

    user = User(
        name=name,
        username=username,
        email=email,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        role=role,
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "User created successfully.",
        "user": _user_json(user),
    }), 201


@api.route("/admin/users/<int:user_id>", methods=["PUT"])
@login_required
def admin_update_user_api(user_id):
    access_error = _admin_required()
    if access_error:
        return access_error

    user = db.session.get(User, user_id)
    if not user:
        return _error("User not found.", 404)

    payload = request.get_json(silent=True) or {}

    name = str(payload.get("name", user.name)).strip()
    username = str(payload.get("username", user.username)).strip()
    email = str(payload.get("email", user.email)).strip().lower()
    role = str(payload.get("role", user.role)).strip().lower()
    password = str(payload.get("password", ""))

    if not name or not username or not email:
        return _error("Name, username, and email are required.")

    if role not in {"user", "admin"}:
        return _error("Invalid user role.")

    existing_username = User.query.filter(
        User.username == username,
        User.id != user.id
    ).first()

    if existing_username:
        return _error("Username already exists.", 409)

    existing_email = User.query.filter(
        User.email == email,
        User.id != user.id
    ).first()

    if existing_email:
        return _error("Email already exists.", 409)

    if user.id == current_user.id and role != "admin":
        return _error("You cannot remove administrator access from your own account.")

    user.name = name
    user.username = username
    user.email = email
    user.role = role

    if password:
        if len(password) < 6:
            return _error("Password must contain at least 6 characters.")
        user.password_hash = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

    db.session.commit()

    return jsonify({
        "message": "User updated successfully.",
        "user": _user_json(user),
    })


@api.route("/admin/users/<int:user_id>", methods=["DELETE"])
@login_required
def admin_delete_user_api(user_id):
    access_error = _admin_required()
    if access_error:
        return access_error

    user = db.session.get(User, user_id)
    if not user:
        return _error("User not found.", 404)

    if user.id == current_user.id:
        return _error("You cannot delete your own account.")

    if user.role == "admin":
        admin_count = User.query.filter_by(role="admin").count()
        if admin_count <= 1:
            return _error("The last administrator cannot be deleted.")

    db.session.delete(user)
    db.session.commit()

    return jsonify({
        "message": "User deleted successfully."
    })


# =====================================================================
# ADMIN DASHBOARD
# =====================================================================

@api.route("/admin/dashboard", methods=["GET"])
@login_required
def admin_dashboard_api():
    if current_user.role != "admin":
        return jsonify({"error": "Administrator access required."}), 403

    now = datetime.utcnow()
    total_users = User.query.count()
    admin_users = User.query.filter_by(role="admin").count()
    regular_users = User.query.filter_by(role="user").count()
    total_resumes = Resume.query.count()
    total_analyses = ResumeAnalysis.query.count()
    total_skill_gaps = SkillGap.query.count()
    total_job_descriptions = JobDescription.query.count()
    total_comparisons = JDComparison.query.count()
    total_recommendations = CareerRecommendation.query.count()

    skill_gap_rows = (
        db.session.query(
            SkillGap.skill_name,
            func.count(SkillGap.id).label("count"),
        )
        .group_by(SkillGap.skill_name)
        .order_by(func.count(SkillGap.id).desc())
        .limit(8)
        .all()
    )

    recommendation_rows = (
        db.session.query(
            CareerRecommendation.career_title,
            func.count(CareerRecommendation.id).label("count"),
        )
        .group_by(CareerRecommendation.career_title)
        .order_by(func.count(CareerRecommendation.id).desc())
        .limit(8)
        .all()
    )

    recent_users = (
        User.query
        .order_by(User.created_at.desc())
        .limit(5)
        .all()
    )

    recent_resumes = (
        Resume.query
        .order_by(Resume.uploaded_at.desc())
        .limit(5)
        .all()
    )

    recent_comparisons = (
        JDComparison.query
        .order_by(JDComparison.compared_at.desc())
        .limit(5)
        .all()
    )

    recent_recommendations = (
        CareerRecommendation.query
        .order_by(CareerRecommendation.created_at.desc())
        .limit(5)
        .all()
    )

    activities = []

    for user in recent_users:
        activities.append({
            "type": "user",
            "icon": "person_add",
            "title": "New user registered",
            "subtitle": user.name,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        })

    for resume in recent_resumes:
        activities.append({
            "type": "resume",
            "icon": "upload_file",
            "title": "Resume uploaded",
            "subtitle": resume.file_name,
            "created_at": resume.uploaded_at.isoformat() if resume.uploaded_at else None,
        })

    for comparison in recent_comparisons:
        job_description = JobDescription.query.get(
            comparison.job_description_id
        )
        job_title = (
            job_description.job_title
            if job_description
            else "Job description"
        )
        activities.append({
            "type": "comparison",
            "icon": "compare_arrows",
            "title": "JD comparison completed",
            "subtitle": job_title,
            "created_at": comparison.compared_at.isoformat() if comparison.compared_at else None,
        })

    for recommendation in recent_recommendations:
        activities.append({
            "type": "recommendation",
            "icon": "route",
            "title": "Career recommendation created",
            "subtitle": recommendation.career_title,
            "created_at": recommendation.created_at.isoformat() if recommendation.created_at else None,
        })

    activities.sort(
        key=lambda item: item["created_at"] or "",
        reverse=True,
    )

    growth_rows = []
    for offset in range(6, -1, -1):
        day = (now - timedelta(days=offset)).date()
        next_day = day + timedelta(days=1)
        count = (
            User.query
            .filter(
                User.created_at >= datetime.combine(day, datetime.min.time()),
                User.created_at < datetime.combine(next_day, datetime.min.time()),
            )
            .count()
        )
        growth_rows.append({
            "date": day.strftime("%d %b"),
            "count": count,
        })

    return jsonify({
        "stats": {
            "total_users": total_users,
            "admin_users": admin_users,
            "regular_users": regular_users,
            "total_resumes": total_resumes,
            "total_analyses": total_analyses,
            "total_skill_gaps": total_skill_gaps,
            "total_job_descriptions": total_job_descriptions,
            "total_comparisons": total_comparisons,
            "total_recommendations": total_recommendations,
        },
        "skill_gaps": [
            {
                "name": skill_name,
                "count": count,
            }
            for skill_name, count in skill_gap_rows
        ],
        "career_recommendations": [
            {
                "name": career_title,
                "count": count,
            }
            for career_title, count in recommendation_rows
        ],
        "recent_activity": activities[:10],
        "user_growth": growth_rows,
    })

