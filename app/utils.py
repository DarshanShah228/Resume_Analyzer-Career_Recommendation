"""
Utility helpers used across the backend:
    - allowed resume file validation
    - text extraction from PDF / DOCX / TXT resumes
    - safe, unique file saving
    - cached loading of the reference JSON data (skills, job roles, tips)
"""

import os
import json
import uuid

from flask import current_app
from werkzeug.utils import secure_filename


# =============================================================
# FILE VALIDATION & SAVING
# =============================================================

def allowed_file(filename):
    """Check the uploaded file has an allowed resume extension."""
    if "." not in filename:
        return False

    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_RESUME_EXTENSIONS"]


def save_resume_file(file_storage, user_id):
    """
    Save an uploaded FileStorage object to disk with a unique,
    collision-proof filename. Returns (stored_filename, absolute_path).
    """
    original_name = secure_filename(file_storage.filename)
    ext = original_name.rsplit(".", 1)[1].lower()

    unique_name = f"user{user_id}_{uuid.uuid4().hex[:10]}.{ext}"

    upload_folder = current_app.config["RESUME_UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    absolute_path = os.path.join(upload_folder, unique_name)
    file_storage.save(absolute_path)

    return original_name, unique_name, absolute_path


# =============================================================
# TEXT EXTRACTION
# =============================================================

def extract_text_from_file(absolute_path, ext):
    """
    Extract raw text from a resume file on disk.
    Supports: pdf, docx, doc (best-effort), txt.
    Returns a plain string (possibly empty if extraction fails).
    """
    ext = ext.lower()

    try:
        if ext == "pdf":
            return _extract_from_pdf(absolute_path)
        elif ext in ("docx", "doc"):
            return _extract_from_docx(absolute_path)
        elif ext == "txt":
            return _extract_from_txt(absolute_path)
    except Exception as exc:
        current_app.logger.warning(f"Text extraction failed for {absolute_path}: {exc}")
        return ""

    return ""


def _extract_from_pdf(path):
    from pypdf import PdfReader

    reader = PdfReader(path)
    text_parts = []

    for page in reader.pages:
        page_text = page.extract_text() or ""
        text_parts.append(page_text)

    return "\n".join(text_parts)


def _extract_from_docx(path):
    import docx

    document = docx.Document(path)
    paragraphs = [p.text for p in document.paragraphs]

    # also grab text inside tables (common in resumes)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                paragraphs.append(cell.text)

    return "\n".join(paragraphs)


def _extract_from_txt(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


# =============================================================
# REFERENCE DATA LOADING (skills.json, job_roles.json, recommendations.json)
# =============================================================

def _load_json(filename):
    data_folder = current_app.config["DATA_FOLDER"]
    path = os.path.join(data_folder, filename)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_skills_taxonomy():
    """Returns dict: { category: [skill, ...] } """
    return _load_json("skills.json")


def get_flat_skill_list():
    """Returns a flat list of every known skill (for matching against text)."""
    taxonomy = get_skills_taxonomy()
    flat = []
    for skills in taxonomy.values():
        flat.extend(skills)
    return flat


def get_job_roles():
    """Returns dict: { role_id: {title, required_skills} } """
    return _load_json("job_roles.json")


def get_recommendations_data():
    """Returns dict with 'skill_recommendations', 'action_verbs', 'impact_phrases'."""
    return _load_json("recommendations.json")
