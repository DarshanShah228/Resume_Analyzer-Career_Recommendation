from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_user, logout_user, login_required, current_user


from app import db, bcrypt
from app.models import User

from sqlalchemy import func
from datetime import datetime, timedelta

from app.models import (
    User,
    Resume,
    ResumeAnalysis,
    SkillGap,
    JobDescription,
    JDComparison,
    CareerRecommendation
)

main = Blueprint("main", __name__)


def admin_required(view):
    from functools import wraps

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


# Home

@main.route("/")
def home():
    return render_template("index.html")


# Authentication

@main.route("/login", methods=["GET", "POST"])
@main.route("/login", methods=["GET", "POST"])
@main.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("main.admin"))

        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        selected_role = request.form.get("role", "user").strip().lower()

        user = User.query.filter_by(username=username).first()

        # User does not exist
        if not user:
            flash("Invalid username or password.", "danger")
            return render_template("login.html")

        # Wrong password
        if not bcrypt.check_password_hash(user.password_hash, password):
            flash("Invalid username or password.", "danger")
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

        # Invalid role value
        logout_user()
        flash("Invalid login role selected.", "danger")
        return render_template("login.html")

    return render_template("login.html")

@main.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("signup.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("signup.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("signup.html")

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return render_template("signup.html")

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return render_template("signup.html")

        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        user = User(
            name=name,
            username=username,
            email=email,
            password_hash=password_hash,
            role="user",
        )
        db.session.add(user)
        db.session.commit()

        flash("Account created successfully. Please login.", "success")
        return redirect(url_for("main.login"))

    return render_template("signup.html")


@main.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.login"))


# User Dashboard

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


# Admin Dashboard

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


@main.route("/admin/reports")
@admin_required
def admin_reports():
    period = request.args.get("period", "30")
    job_role = request.args.get("job_role", "all")

    today = datetime.utcnow()

    if period == "7":
        start_date = today - timedelta(days=7)
    elif period == "30":
        start_date = today - timedelta(days=30)
    elif period == "90":
        start_date = today - timedelta(days=90)
    elif period == "365":
        start_date = today - timedelta(days=365)
    else:
        start_date = None

    # -----------------------------------
    # Find resumes for selected career role
    # -----------------------------------

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
            row[0] for row in role_query.distinct().all()
        ]

    # -----------------------------------
    # Resume Query
    # -----------------------------------

    resume_query = Resume.query

    if start_date:
        resume_query = resume_query.filter(
            Resume.uploaded_at >= start_date
        )

    if filtered_resume_ids is not None:
        resume_query = resume_query.filter(
            Resume.id.in_(filtered_resume_ids)
        )

    total_resumes = resume_query.count()

    # -----------------------------------
    # Users
    # -----------------------------------

    if filtered_resume_ids is None:
        total_users = User.query.filter_by(
            role="user"
        ).count()
    else:
        total_users = db.session.query(
            func.count(func.distinct(Resume.user_id))
        ).filter(
            Resume.id.in_(filtered_resume_ids)
        ).scalar() or 0

    # -----------------------------------
    # Resume Analysis
    # -----------------------------------

    analysis_query = ResumeAnalysis.query

    if start_date:
        analysis_query = analysis_query.filter(
            ResumeAnalysis.analyzed_at >= start_date
        )

    if filtered_resume_ids is not None:
        analysis_query = analysis_query.filter(
            ResumeAnalysis.resume_id.in_(filtered_resume_ids)
        )

    total_analyzed = analysis_query.count()

    # -----------------------------------
    # Average Resume Score
    # -----------------------------------

    avg_resume_score = analysis_query.with_entities(
        func.avg(ResumeAnalysis.resume_score)
    ).scalar()

    avg_resume_score = round(avg_resume_score or 0, 2)

    # -----------------------------------
    # JD Comparisons
    # -----------------------------------

    jd_query = JDComparison.query

    if start_date:
        jd_query = jd_query.filter(
            JDComparison.compared_at >= start_date
        )

    if filtered_resume_ids is not None:
        jd_query = jd_query.filter(
            JDComparison.resume_id.in_(filtered_resume_ids)
        )

    total_comparisons = jd_query.count()

    # -----------------------------------
    # Average JD Match
    # -----------------------------------

    avg_jd_match = jd_query.with_entities(
        func.avg(JDComparison.match_score)
    ).scalar()

    avg_jd_match = round(avg_jd_match or 0, 2)

    # -----------------------------------
    # Career Recommendations
    # -----------------------------------

    recommendation_query = CareerRecommendation.query

    if start_date:
        recommendation_query = recommendation_query.filter(
            CareerRecommendation.created_at >= start_date
        )

    if filtered_resume_ids is not None:
        recommendation_query = recommendation_query.filter(
            CareerRecommendation.resume_id.in_(filtered_resume_ids)
        )

    total_recommendations = recommendation_query.count()

    # -----------------------------------
    # Top Career Roles
    # -----------------------------------

    role_query = db.session.query(
        CareerRecommendation.career_title,
        func.count(CareerRecommendation.id).label("count")
    )

    if start_date:
        role_query = role_query.filter(
            CareerRecommendation.created_at >= start_date
        )

    if filtered_resume_ids is not None:
        role_query = role_query.filter(
            CareerRecommendation.resume_id.in_(filtered_resume_ids)
        )

    role_query = role_query.group_by(
        CareerRecommendation.career_title
    ).order_by(
        func.count(CareerRecommendation.id).desc()
    ).limit(10)

    top_roles = role_query.all()

    role_labels = [row.career_title for row in top_roles]
    role_counts = [row.count for row in top_roles]

    # -----------------------------------
    # Skill Gaps
    # -----------------------------------

    skill_gap_query = db.session.query(
        SkillGap.skill_name,
        func.count(SkillGap.id).label("count")
    )

    if filtered_resume_ids is not None:
        skill_gap_query = skill_gap_query.filter(
            SkillGap.resume_id.in_(filtered_resume_ids)
        )

    skill_gaps = skill_gap_query.group_by(
        SkillGap.skill_name
    ).order_by(
        func.count(SkillGap.id).desc()
    ).limit(10).all()

    skill_labels = [row.skill_name for row in skill_gaps]
    skill_counts = [row.count for row in skill_gaps]

    # -----------------------------------
    # Resume Score Distribution
    # -----------------------------------

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

    # -----------------------------------
    # JD Match Distribution
    # -----------------------------------

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

    # -----------------------------------
    # Career Roles for Filter
    # -----------------------------------

    all_roles = db.session.query(
        CareerRecommendation.career_title
    ).distinct().order_by(
        CareerRecommendation.career_title
    ).all()

    all_roles = [role[0] for role in all_roles]

    # -----------------------------------
    # Render Page
    # -----------------------------------

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
        score_labels=list(score_distribution.keys()),
        score_counts=list(score_distribution.values()),
        match_labels=list(match_distribution.keys()),
        match_counts=list(match_distribution.values()),
        selected_period=period,
        selected_role=job_role,
        all_roles=all_roles
    )