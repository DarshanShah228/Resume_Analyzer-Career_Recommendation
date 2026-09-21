from datetime import datetime
from app import db
from flask_login import UserMixin


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    resumes = db.relationship(
        "Resume",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    job_descriptions = db.relationship(
        "JobDescription",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )


class Resume(db.Model):
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500))
    extracted_text = db.Column(db.Text)

    uploaded_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    analysis = db.relationship(
        "ResumeAnalysis",
        backref="resume",
        uselist=False,
        cascade="all, delete-orphan"
    )

    skill_gaps = db.relationship(
        "SkillGap",
        backref="resume",
        lazy=True,
        cascade="all, delete-orphan"
    )

    comparisons = db.relationship(
        "JDComparison",
        backref="resume",
        lazy=True,
        cascade="all, delete-orphan"
    )

    recommendations = db.relationship(
        "CareerRecommendation",
        backref="resume",
        lazy=True,
        cascade="all, delete-orphan"
    )


class ResumeAnalysis(db.Model):
    __tablename__ = "resume_analysis"

    id = db.Column(db.Integer, primary_key=True)

    resume_id = db.Column(
        db.Integer,
        db.ForeignKey("resumes.id"),
        nullable=False,
        unique=True
    )

    resume_score = db.Column(db.Float, default=0)

    skills = db.Column(db.Text)
    experience = db.Column(db.Text)
    education = db.Column(db.Text)

    analysis_result = db.Column(db.Text)

    analyzed_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class SkillGap(db.Model):
    __tablename__ = "skill_gaps"

    id = db.Column(db.Integer, primary_key=True)

    resume_id = db.Column(
        db.Integer,
        db.ForeignKey("resumes.id"),
        nullable=False
    )

    skill_name = db.Column(
        db.String(100),
        nullable=False
    )

    skill_level = db.Column(
        db.String(50)
    )

    recommendation = db.Column(
        db.Text
    )


class JobDescription(db.Model):
    __tablename__ = "job_descriptions"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    job_title = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    comparisons = db.relationship(
        "JDComparison",
        backref="job_description",
        lazy=True,
        cascade="all, delete-orphan"
    )


class JDComparison(db.Model):
    __tablename__ = "jd_comparisons"

    id = db.Column(db.Integer, primary_key=True)

    resume_id = db.Column(
        db.Integer,
        db.ForeignKey("resumes.id"),
        nullable=False
    )

    job_description_id = db.Column(
        db.Integer,
        db.ForeignKey("job_descriptions.id"),
        nullable=False
    )

    match_score = db.Column(
        db.Float,
        default=0
    )

    matched_skills = db.Column(db.Text)
    missing_skills = db.Column(db.Text)

    compared_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class CareerRecommendation(db.Model):
    __tablename__ = "career_recommendations"

    id = db.Column(db.Integer, primary_key=True)

    resume_id = db.Column(
        db.Integer,
        db.ForeignKey("resumes.id"),
        nullable=False
    )

    career_title = db.Column(
        db.String(150),
        nullable=False
    )

    match_percentage = db.Column(
        db.Float,
        default=0
    )

    recommendation = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )