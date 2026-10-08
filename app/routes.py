from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    send_file
)

from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user
)

from app import db, bcrypt

from app.models import (
    User,
    Resume,
    ResumeAnalysis,
    SkillGap,
    JobDescription,
    JDComparison,
    CareerRecommendation
)

from sqlalchemy import func
from datetime import datetime, timedelta

import json
import re
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)


main = Blueprint("main", __name__)


# =========================================================
# ADMIN ACCESS
# =========================================================

def admin_required(view):
    from functools import wraps

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)

        return view(*args, **kwargs)

    return wrapped


# =========================================================
# HOME
# =========================================================

@main.route("/")
def home():
    return render_template("index.html")


# =========================================================
# AUTHENTICATION
# =========================================================

@main.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:

        if current_user.role == "admin":
            return redirect(url_for("main.admin"))

        return redirect(url_for("main.dashboard"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        selected_role = request.form.get(
            "role",
            "user"
        ).strip().lower()

        user = User.query.filter_by(
            username=username
        ).first()

        # User does not exist
        if not user:

            flash(
                "Invalid username or password.",
                "danger"
            )

            return render_template("login.html")

        # Wrong password
        if not bcrypt.check_password_hash(
            user.password_hash,
            password
        ):

            flash(
                "Invalid username or password.",
                "danger"
            )

            return render_template("login.html")

        # Normal user cannot access Admin Panel
        if selected_role == "admin" and user.role != "admin":

            flash(
                "You do not have administrator access. Please select User / Candidate.",
                "danger"
            )

            return render_template("login.html")

        # Login successful
        login_user(user)

        # User/Candidate selected
        if selected_role == "user":
            return redirect(url_for("main.dashboard"))

        # Administrator selected
        if selected_role == "admin":
            return redirect(url_for("main.admin"))

        # Invalid role
        logout_user()

        flash(
            "Invalid login role selected.",
            "danger"
        )

        return render_template("login.html")

    return render_template("login.html")


@main.route("/signup", methods=["GET", "POST"])
def signup():

    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        username = request.form.get(
            "username",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not name or not username or not email or not password:

            flash(
                "All fields are required.",
                "danger"
            )

            return render_template("signup.html")

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return render_template("signup.html")

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters long.",
                "danger"
            )

            return render_template("signup.html")

        if User.query.filter_by(
            username=username
        ).first():

            flash(
                "Username already exists.",
                "danger"
            )

            return render_template("signup.html")

        if User.query.filter_by(
            email=email
        ).first():

            flash(
                "Email already registered.",
                "danger"
            )

            return render_template("signup.html")

        password_hash = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

        user = User(
            name=name,
            username=username,
            email=email,
            password_hash=password_hash,
            role="user"
        )

        db.session.add(user)
        db.session.commit()

        flash(
            "Account created successfully. Please login.",
            "success"
        )

        return redirect(url_for("main.login"))

    return render_template("signup.html")


@main.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(url_for("main.login"))


# =========================================================
# FORGOT PASSWORD
# =========================================================

@main.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if (
            not username
            or not email
            or not password
            or not confirm_password
        ):

            flash(
                "All fields are required.",
                "danger"
            )

            return render_template(
                "forgot-password.html"
            )

        user = User.query.filter_by(
            username=username
        ).first()

        if not user or user.email.lower() != email:

            flash(
                "No account matches that username and email combination.",
                "danger"
            )

            return render_template(
                "forgot-password.html"
            )

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters long.",
                "danger"
            )

            return render_template(
                "forgot-password.html"
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return render_template(
                "forgot-password.html"
            )

        user.password_hash = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

        db.session.commit()

        flash(
            "Password updated successfully. Please log in with your new password.",
            "success"
        )

        return redirect(url_for("main.login"))

    return render_template("forgot-password.html")


# =========================================================
# USER DASHBOARD
# =========================================================

@main.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@main.route("/upload-resume")
@login_required
def upload_resume():
    return render_template("upload-resume.html")


@main.route("/resume-analysis")
@login_required
def resume_analysis():
    return render_template("resume-analysis.html")


# =========================================================
# DOWNLOAD RESUME PDF REPORT
# =========================================================

@main.route("/download-resume-report")
@login_required
def download_resume_report():

    try:

        # -----------------------------------------------------
        # Get latest resume of logged-in user
        # -----------------------------------------------------

        resume = (
            Resume.query
            .filter_by(
                user_id=current_user.id
            )
            .order_by(
                Resume.uploaded_at.desc()
            )
            .first()
        )

        if not resume:

            flash(
                "No resume found. Please upload a resume first.",
                "warning"
            )

            return redirect(
                url_for("main.resume_analysis")
            )

        # -----------------------------------------------------
        # Check analysis
        # -----------------------------------------------------

        if not resume.analysis:

            flash(
                "Resume analysis is not available yet. Please analyze your resume first.",
                "warning"
            )

            return redirect(
                url_for("main.resume_analysis")
            )

        analysis = resume.analysis

        # -----------------------------------------------------
        # Read analysis JSON
        # -----------------------------------------------------

        try:

            analysis_result = json.loads(
                analysis.analysis_result or "{}"
            )

        except (
            TypeError,
            ValueError
        ):

            analysis_result = {}

        # -----------------------------------------------------
        # Candidate Name
        # -----------------------------------------------------

        candidate_name = analysis_result.get(
            "candidate_name"
        )

        if not candidate_name:

            candidate_name = (
                current_user.name
                or current_user.username
                or "Candidate"
            )

        # -----------------------------------------------------
        # Overall Score
        # -----------------------------------------------------

        overall_score = analysis.resume_score or 0

        # -----------------------------------------------------
        # Sub Scores
        # -----------------------------------------------------

        sub_scores = analysis_result.get(
            "sub_scores",
            {}
        )

        ats_format = sub_scores.get(
            "ats_format",
            0
        )

        skill_extraction = sub_scores.get(
            "skill_extraction",
            0
        )

        impact = sub_scores.get(
            "impact",
            0
        )

        keywords = sub_scores.get(
            "keywords",
            0
        )

        # -----------------------------------------------------
        # Strengths
        # -----------------------------------------------------

        strengths = analysis_result.get(
            "strengths",
            []
        )

        if not isinstance(
            strengths,
            list
        ):

            strengths = [
                strengths
            ]

        # -----------------------------------------------------
        # Improvements
        # -----------------------------------------------------

        improvements = analysis_result.get(
            "improvements",
            []
        )

        if not isinstance(
            improvements,
            list
        ):

            improvements = [
                improvements
            ]

        # -----------------------------------------------------
        # Skills
        # -----------------------------------------------------

        skills_by_category = analysis_result.get(
            "skills_by_category",
            {}
        )

        # -----------------------------------------------------
        # Education
        # -----------------------------------------------------

        try:

            education = json.loads(
                analysis.education or "[]"
            )

        except (
            TypeError,
            ValueError
        ):

            education = []

        # -----------------------------------------------------
        # Experience
        # -----------------------------------------------------

        try:

            experience = json.loads(
                analysis.experience or "{}"
            )

        except (
            TypeError,
            ValueError
        ):

            experience = {}

        # -----------------------------------------------------
        # Create PDF in memory
        # -----------------------------------------------------

        buffer = BytesIO()

        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm
        )

        # =====================================================
        # PDF STYLES
        # =====================================================

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "CareerAITitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4F46E5"),
            spaceAfter=5
        )

        subtitle_style = ParagraphStyle(
            "CareerAISubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=18
        )

        section_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=14,
            spaceAfter=8
        )

        normal_style = ParagraphStyle(
            "NormalText",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#334155"),
            spaceAfter=5
        )

        small_style = ParagraphStyle(
            "SmallText",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748B")
        )

        bullet_style = ParagraphStyle(
            "BulletText",
            parent=normal_style,
            leftIndent=10,
            firstLineIndent=-8,
            spaceAfter=5
        )

        score_style = ParagraphStyle(
            "Score",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4F46E5")
        )

        # =====================================================
        # PDF STORY
        # =====================================================

        story = []

        # -----------------------------------------------------
        # Header
        # -----------------------------------------------------

        story.append(
            Paragraph(
                "CareerAI",
                title_style
            )
        )

        story.append(
            Paragraph(
                "Resume Analysis Report",
                subtitle_style
            )
        )

        # -----------------------------------------------------
        # Candidate Information
        # -----------------------------------------------------

        story.append(
            Paragraph(
                "Candidate Information",
                section_style
            )
        )

        upload_date = (
            resume.uploaded_at.strftime(
                "%d %B %Y"
            )
            if resume.uploaded_at
            else "N/A"
        )

        analyzed_date = (
            analysis.analyzed_at.strftime(
                "%d %B %Y"
            )
            if analysis.analyzed_at
            else "N/A"
        )

        candidate_table_data = [
            [
                "Candidate Name",
                str(candidate_name)
            ],
            [
                "Resume File",
                str(resume.file_name)
            ],
            [
                "Uploaded On",
                upload_date
            ],
            [
                "Analyzed On",
                analyzed_date
            ]
        ]

        candidate_table = Table(
            candidate_table_data,
            colWidths=[
                48 * mm,
                122 * mm
            ]
        )

        candidate_table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#F1F5F9")
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (0, -1),
                    "Helvetica-Bold"
                ),
                (
                    "FONTNAME",
                    (1, 0),
                    (1, -1),
                    "Helvetica"
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#334155")
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#CBD5E1")
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    9
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                )
            ])
        )

        story.append(
            candidate_table
        )

        # -----------------------------------------------------
        # Overall Resume Score
        # -----------------------------------------------------

        story.append(
            Paragraph(
                "Overall Resume Score",
                section_style
            )
        )

        score_table = Table(
            [
                [
                    Paragraph(
                        f"{overall_score:.0f} / 100",
                        score_style
                    )
                ]
            ],
            colWidths=[
                170 * mm
            ]
        )

        score_table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#EEF2FF")
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    1,
                    colors.HexColor("#6366F1")
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    14
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    14
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER"
                )
            ])
        )

        story.append(
            score_table
        )

        # -----------------------------------------------------
        # Score Breakdown
        # -----------------------------------------------------

        story.append(
            Paragraph(
                "Score Breakdown",
                section_style
            )
        )

        score_data = [
            [
                "Metric",
                "Score"
            ],
            [
                "ATS Format",
                f"{ats_format}%"
            ],
            [
                "Skill Extraction",
                f"{skill_extraction}%"
            ],
            [
                "Impact",
                f"{impact}%"
            ],
            [
                "Keywords",
                f"{keywords}%"
            ]
        ]

        score_breakdown_table = Table(
            score_data,
            colWidths=[
                125 * mm,
                45 * mm
            ]
        )

        score_breakdown_table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#4F46E5")
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),
                (
                    "FONTNAME",
                    (0, 1),
                    (-1, -1),
                    "Helvetica"
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    9
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#CBD5E1")
                ),
                (
                    "ALIGN",
                    (1, 0),
                    (1, -1),
                    "CENTER"
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                )
            ])
        )

        story.append(
            score_breakdown_table
        )

        # -----------------------------------------------------
        # Top Strengths
        # -----------------------------------------------------

        story.append(
            Paragraph(
                "Top Strengths",
                section_style
            )
        )

        if strengths:

            for strength in strengths:

                story.append(
                    Paragraph(
                        f"• {str(strength)}",
                        bullet_style
                    )
                )

        else:

            story.append(
                Paragraph(
                    "No strengths identified.",
                    normal_style
                )
            )

        # -----------------------------------------------------
        # Areas for Improvement
        # -----------------------------------------------------

        story.append(
            Paragraph(
                "Areas for Improvement",
                section_style
            )
        )

        if improvements:

            for improvement in improvements:

                story.append(
                    Paragraph(
                        f"• {str(improvement)}",
                        bullet_style
                    )
                )

        else:

            story.append(
                Paragraph(
                    "No improvement areas identified.",
                    normal_style
                )
            )

        # -----------------------------------------------------
        # Extracted Skills
        # -----------------------------------------------------

        story.append(
            Paragraph(
                "Extracted Skills",
                section_style
            )
        )

        if skills_by_category:

            skill_data = [
                [
                    "Category",
                    "Skills"
                ]
            ]

            for category, skills in skills_by_category.items():

                if isinstance(
                    skills,
                    list
                ):

                    skill_text = ", ".join(
                        str(skill)
                        for skill in skills
                    )

                else:

                    skill_text = str(
                        skills
                    )

                skill_data.append(
                    [
                        str(category),
                        skill_text
                    ]
                )

            skill_table = Table(
                skill_data,
                colWidths=[
                    45 * mm,
                    125 * mm
                ],
                repeatRows=1
            )

            skill_table.setStyle(
                TableStyle([
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#4F46E5")
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold"
                    ),
                    (
                        "FONTNAME",
                        (0, 1),
                        (-1, -1),
                        "Helvetica"
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#CBD5E1")
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP"
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        7
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        7
                    )
                ])
            )

            story.append(
                skill_table
            )

        else:

            story.append(
                Paragraph(
                    "No recognized skills found.",
                    normal_style
                )
            )

        # -----------------------------------------------------
        # Education
        # -----------------------------------------------------

        if education:

            story.append(
                Paragraph(
                    "Education",
                    section_style
                )
            )

            if isinstance(
                education,
                list
            ):

                for item in education:

                    story.append(
                        Paragraph(
                            f"• {str(item)}",
                            bullet_style
                        )
                    )

            else:

                story.append(
                    Paragraph(
                        str(education),
                        normal_style
                    )
                )

        # -----------------------------------------------------
        # Experience
        # -----------------------------------------------------

        if experience:

            story.append(
                Paragraph(
                    "Experience",
                    section_style
                )
            )

            if isinstance(
                experience,
                dict
            ):

                for key, value in experience.items():

                    if isinstance(
                        value,
                        list
                    ):

                        value = ", ".join(
                            str(item)
                            for item in value
                        )

                    story.append(
                        Paragraph(
                            f"<b>{str(key)}:</b> {str(value)}",
                            normal_style
                        )
                    )

            elif isinstance(
                experience,
                list
            ):

                for item in experience:

                    story.append(
                        Paragraph(
                            f"• {str(item)}",
                            bullet_style
                        )
                    )

            else:

                story.append(
                    Paragraph(
                        str(experience),
                        normal_style
                    )
                )

        # -----------------------------------------------------
        # Footer
        # -----------------------------------------------------

        story.append(
            Spacer(
                1,
                15
            )
        )

        story.append(
            Paragraph(
                "Generated by CareerAI - Resume Analyzer & Career Recommendation System",
                small_style
            )
        )

        story.append(
            Paragraph(
                "This report is generated from the resume analysis performed by CareerAI.",
                small_style
            )
        )

        # -----------------------------------------------------
        # Generate PDF
        # -----------------------------------------------------

        document.build(
            story
        )

        buffer.seek(0)

        # -----------------------------------------------------
        # Safe filename
        # -----------------------------------------------------

        safe_name = re.sub(
            r"[^A-Za-z0-9_-]+",
            "_",
            str(candidate_name)
        ).strip("_")

        if not safe_name:
            safe_name = "Candidate"

        filename = (
            f"CareerAI_Resume_Report_{safe_name}.pdf"
        )

        # -----------------------------------------------------
        # Send PDF to browser
        # -----------------------------------------------------

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf"
        )

    except Exception as e:

        print(
            "DOWNLOAD RESUME REPORT ERROR:",
            repr(e)
        )

        flash(
            "Unable to generate the PDF report. Please try again.",
            "danger"
        )

        return redirect(
            url_for("main.resume_analysis")
        )


# =========================================================
# OTHER USER PAGES
# =========================================================

@main.route("/skill-gap")
@login_required
def skill_gap():
    return render_template("skill-gap.html")


@main.route("/compare-jd")
@login_required
def compare_jd():
    return render_template("compare-jd.html")


@main.route("/jd-results")
@login_required
def jd_results():
    return render_template("jd-results.html")


@main.route("/ai-suggestions")
@login_required
def ai_suggestions():
    return render_template("ai-suggestions.html")


@main.route("/about")
def about():
    return render_template("about.html")


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@main.route("/admin")
@admin_required
def admin():
    return render_template("admin/admin.html")


@main.route("/about-admin")
@admin_required
def about_admin():
    return render_template("admin/about-admin.html")


@main.route("/admin-dashboard")
@admin_required
def admin_dashboard():
    return render_template("admin/admin_dashboard.html")


# =========================================================
# ADMIN REPORTS
# =========================================================

@main.route("/admin/reports")
@admin_required
def admin_reports():

    period = request.args.get(
        "period",
        "30"
    )

    job_role = request.args.get(
        "job_role",
        "all"
    )

    today = datetime.utcnow()

    # -----------------------------------------------------
    # Date Filter
    # -----------------------------------------------------

    if period == "7":

        start_date = today - timedelta(
            days=7
        )

    elif period == "30":

        start_date = today - timedelta(
            days=30
        )

    elif period == "90":

        start_date = today - timedelta(
            days=90
        )

    elif period == "365":

        start_date = today - timedelta(
            days=365
        )

    else:

        start_date = None

    # -----------------------------------------------------
    # Find resumes for selected career role
    # -----------------------------------------------------

    filtered_resume_ids = None

    if job_role != "all":

        role_query = db.session.query(
            CareerRecommendation.resume_id
        ).filter(
            CareerRecommendation.career_title == job_role
        )

        if start_date:

            role_query = role_query.filter(
                CareerRecommendation.created_at >= start_date
            )

        filtered_resume_ids = [
            row[0]
            for row in role_query.distinct().all()
        ]

    # -----------------------------------------------------
    # Resume Query
    # -----------------------------------------------------

    resume_query = Resume.query

    if start_date:

        resume_query = resume_query.filter(
            Resume.uploaded_at >= start_date
        )

    if filtered_resume_ids is not None:

        resume_query = resume_query.filter(
            Resume.id.in_(
                filtered_resume_ids
            )
        )

    total_resumes = resume_query.count()

    # -----------------------------------------------------
    # Users
    # -----------------------------------------------------

    if filtered_resume_ids is None:

        total_users = User.query.filter_by(
            role="user"
        ).count()

    else:

        total_users = db.session.query(
            func.count(
                func.distinct(
                    Resume.user_id
                )
            )
        ).filter(
            Resume.id.in_(
                filtered_resume_ids
            )
        ).scalar() or 0

    # -----------------------------------------------------
    # Resume Analysis
    # -----------------------------------------------------

    analysis_query = ResumeAnalysis.query

    if start_date:

        analysis_query = analysis_query.filter(
            ResumeAnalysis.analyzed_at >= start_date
        )

    if filtered_resume_ids is not None:

        analysis_query = analysis_query.filter(
            ResumeAnalysis.resume_id.in_(
                filtered_resume_ids
            )
        )

    total_analyzed = analysis_query.count()

    # -----------------------------------------------------
    # Average Resume Score
    # -----------------------------------------------------

    avg_resume_score = analysis_query.with_entities(
        func.avg(
            ResumeAnalysis.resume_score
        )
    ).scalar()

    avg_resume_score = round(
        avg_resume_score or 0,
        2
    )

    # -----------------------------------------------------
    # JD Comparisons
    # -----------------------------------------------------

    jd_query = JDComparison.query

    if start_date:

        jd_query = jd_query.filter(
            JDComparison.compared_at >= start_date
        )

    if filtered_resume_ids is not None:

        jd_query = jd_query.filter(
            JDComparison.resume_id.in_(
                filtered_resume_ids
            )
        )

    total_comparisons = jd_query.count()

    # -----------------------------------------------------
    # Average JD Match
    # -----------------------------------------------------

    avg_jd_match = jd_query.with_entities(
        func.avg(
            JDComparison.match_score
        )
    ).scalar()

    avg_jd_match = round(
        avg_jd_match or 0,
        2
    )

    # -----------------------------------------------------
    # Career Recommendations
    # -----------------------------------------------------

    recommendation_query = CareerRecommendation.query

    if start_date:

        recommendation_query = recommendation_query.filter(
            CareerRecommendation.created_at >= start_date
        )

    if filtered_resume_ids is not None:

        recommendation_query = recommendation_query.filter(
            CareerRecommendation.resume_id.in_(
                filtered_resume_ids
            )
        )

    total_recommendations = recommendation_query.count()

    # -----------------------------------------------------
    # Top Career Roles
    # -----------------------------------------------------

    role_query = db.session.query(
        CareerRecommendation.career_title,
        func.count(
            CareerRecommendation.id
        ).label("count")
    )

    if start_date:

        role_query = role_query.filter(
            CareerRecommendation.created_at >= start_date
        )

    if filtered_resume_ids is not None:

        role_query = role_query.filter(
            CareerRecommendation.resume_id.in_(
                filtered_resume_ids
            )
        )

    role_query = (
        role_query
        .group_by(
            CareerRecommendation.career_title
        )
        .order_by(
            func.count(
                CareerRecommendation.id
            ).desc()
        )
        .limit(10)
    )

    top_roles = role_query.all()

    role_labels = [
        row.career_title
        for row in top_roles
    ]

    role_counts = [
        row.count
        for row in top_roles
    ]

    # -----------------------------------------------------
    # Skill Gaps
    # -----------------------------------------------------

    skill_gap_query = db.session.query(
        SkillGap.skill_name,
        func.count(
            SkillGap.id
        ).label("count")
    )

    if filtered_resume_ids is not None:

        skill_gap_query = skill_gap_query.filter(
            SkillGap.resume_id.in_(
                filtered_resume_ids
            )
        )

    skill_gaps = (
        skill_gap_query
        .group_by(
            SkillGap.skill_name
        )
        .order_by(
            func.count(
                SkillGap.id
            ).desc()
        )
        .limit(10)
        .all()
    )

    skill_labels = [
        row.skill_name
        for row in skill_gaps
    ]

    skill_counts = [
        row.count
        for row in skill_gaps
    ]

    # -----------------------------------------------------
    # Resume Score Distribution
    # -----------------------------------------------------

    scores = analysis_query.with_entities(
        ResumeAnalysis.resume_score
    ).all()

    score_distribution = {
        "0-40": 0,
        "41-60": 0,
        "61-80": 0,
        "81-100": 0
    }

    for row in scores:

        score = row[0] or 0

        if score <= 40:

            score_distribution["0-40"] += 1

        elif score <= 60:

            score_distribution["41-60"] += 1

        elif score <= 80:

            score_distribution["61-80"] += 1

        else:

            score_distribution["81-100"] += 1

    # -----------------------------------------------------
    # JD Match Distribution
    # -----------------------------------------------------

    matches = jd_query.with_entities(
        JDComparison.match_score
    ).all()

    match_distribution = {
        "0-30": 0,
        "31-50": 0,
        "51-70": 0,
        "71-90": 0,
        "91-100": 0
    }

    for row in matches:

        score = row[0] or 0

        if score <= 30:

            match_distribution["0-30"] += 1

        elif score <= 50:

            match_distribution["31-50"] += 1

        elif score <= 70:

            match_distribution["51-70"] += 1

        elif score <= 90:

            match_distribution["71-90"] += 1

        else:

            match_distribution["91-100"] += 1

    # -----------------------------------------------------
    # Career Roles Filter
    # -----------------------------------------------------

    all_roles = db.session.query(
        CareerRecommendation.career_title
    ).distinct().order_by(
        CareerRecommendation.career_title
    ).all()

    all_roles = [
        role[0]
        for role in all_roles
    ]

    # -----------------------------------------------------
    # Render Page
    # -----------------------------------------------------

    return render_template(
        "admin/admin_reports.html",
        total_users=total_users,
        total_resumes=total_resumes,
        total_analyzed=total_analyzed,
        total_comparisons=total_comparisons,
        total_recommendations=total_recommendations,
        avg_resume_score=avg_resume_score,
        avg_jd_match=avg_jd_match,
        role_labels=role_labels,
        role_counts=role_counts,
        skill_labels=skill_labels,
        skill_counts=skill_counts,
        score_labels=list(
            score_distribution.keys()
        ),
        score_counts=list(
            score_distribution.values()
        ),
        match_labels=list(
            match_distribution.keys()
        ),
        match_counts=list(
            match_distribution.values()
        ),
        selected_period=period,
        selected_role=job_role,
        all_roles=all_roles
    )