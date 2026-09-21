import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "careerai-development-secret-key")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "resume_analyzer.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Folder where uploaded resume files are physically stored
    RESUME_UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "resumes")

    # Folder holding the read-only reference JSON data (skills, roles, tips)
    DATA_FOLDER = os.path.join(BASE_DIR, "data")

    ALLOWED_RESUME_EXTENSIONS = {"pdf", "docx", "doc", "txt"}

    # 5 MB max upload size
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
