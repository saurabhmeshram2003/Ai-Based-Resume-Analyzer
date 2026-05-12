"""
ResumeAI — Free Public Resume Analyzer
No login required. Open to all users. ATS scoring, PDF reports, AI suggestions.
"""
import os
import uuid
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    jsonify, flash, send_file
)

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-CHANGE-IN-PRODUCTION")

# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["resume_analyzer"]

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["300 per day", "60 per hour"],
    storage_uri="memory://",
)

# ---------------------------------------------------------------------------
# Import app modules (after db is initialised)
# ---------------------------------------------------------------------------
from models.analysis     import AnalysisModel
from utils.file_parser   import extract_text
from utils.scorer        import compute_score
from utils.suggestions   import generate_suggestions, rewrite_with_openai, rewrite_bullet
from utils.pdf_report    import generate_pdf_report

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
UPLOAD_FOLDER      = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE      = 2 * 1024 * 1024          # 2 MB
ALLOWED_MIMETYPES  = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}

JOB_ROLES = [
    "Software Engineer", "Senior Software Engineer", "Full Stack Developer",
    "Frontend Developer", "Backend Developer", "DevOps Engineer",
    "Data Scientist", "Data Engineer", "Machine Learning Engineer",
    "Product Manager", "UI/UX Designer", "Cloud Architect",
    "Cybersecurity Analyst", "QA Engineer", "Mobile Developer",
    "Business Analyst", "Project Manager", "General / Other",
]

SAMPLE_JD = """We are looking for a skilled Software Engineer to join our team.

Requirements:
- 3+ years of experience with Python and JavaScript
- Proficiency in React, Node.js, and REST APIs
- Experience with MongoDB, PostgreSQL, or Redis
- Familiarity with Docker, Kubernetes, and AWS/GCP
- Experience with CI/CD pipelines (GitHub Actions, Jenkins)
- Strong knowledge of data structures, algorithms, and system design
- Excellent communication and problem-solving skills

Nice to have:
- Experience with machine learning frameworks (TensorFlow, PyTorch)
- Knowledge of microservices architecture
- Agile/Scrum experience
"""

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def validate_file(file) -> tuple[bool, str]:
    """Returns (is_valid, error_message)."""
    if not file or not file.filename:
        return False, "No file selected."

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, "Only PDF and DOCX files are allowed."

    content = file.read()
    if len(content) > MAX_FILE_SIZE:
        return False, "File exceeds the 2 MB size limit."

    # Restore stream pointer
    file.seek(0)
    return True, ""


# ---------------------------------------------------------------------------
# Context processor
# ---------------------------------------------------------------------------
@app.context_processor
def inject_globals():
    return {
        "job_roles":    JOB_ROLES,
        "now":          datetime.utcnow(),
    }


# ===========================================================================
# PUBLIC ROUTES
# ===========================================================================

@app.get("/")
def index():
    """Landing page."""
    return render_template("index.html")


@app.get("/analyzer")
def analyzer():
    """Main analyzer tool page."""
    return render_template("analyzer.html", sample_jd=SAMPLE_JD, job_roles=JOB_ROLES)


# ---------------------------------------------------------------------------
# Core: analyze endpoint
# ---------------------------------------------------------------------------
@app.post("/analyze")
@limiter.limit("10 per minute")
def analyze():
    """Process uploaded resume against a job description."""

    # ---- File validation --------------------------------------------------
    file = request.files.get("resume")
    is_valid, err = validate_file(file)
    if not is_valid:
        flash(err, "error")
        return redirect(url_for("analyzer"))

    ext           = os.path.splitext(file.filename)[1].lower()
    safe_name     = f"{uuid.uuid4()}{ext}"
    file_path     = os.path.join(UPLOAD_FOLDER, safe_name)
    original_name = file.filename

    # ---- JD & role --------------------------------------------------------
    job_description = request.form.get("job_description", "").strip()
    if not job_description:
        flash("Please paste a job description.", "error")
        return redirect(url_for("analyzer"))
    job_role = request.form.get("job_role", "General / Other")

    # ---- Save temp file, extract text, clean up ---------------------------
    try:
        file.save(file_path)
        resume_text = extract_text(file_path)
    except Exception as e:
        flash(f"Could not parse your resume: {e}", "error")
        return redirect(url_for("analyzer"))
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass

    if not resume_text.strip():
        flash("Couldn't extract text from the file. Make sure it is not scanned/image-only.", "error")
        return redirect(url_for("analyzer"))

    # ---- Scoring ----------------------------------------------------------
    result = compute_score(resume_text, job_description)
    result["resume_text_sample"] = resume_text[:500]   # for suggestion engine
    suggestions = generate_suggestions(result)

    # ---- Persist ----------------------------------------------------------
    analysis_doc = {
        "user_id":               None,
        "filename":              original_name,
        "job_role":              job_role,
        "job_description":       job_description[:600],
        "score":                 result["score"],
        "score_label":           result["score_label"],
        "score_color":           result["score_color"],
        "skill_match_score":     result["skill_match_score"],
        "keyword_density_score": result["keyword_density_score"],
        "experience_score":      result["experience_score"],
        "structure_score":       result["structure_score"],
        "formatting_score":      result["formatting_score"],
        "matched_skills":        result["matched_skills"],
        "missing_skills":        result["missing_skills"],
        "missing_skills_with_priority": result["missing_skills_with_priority"],
        "matched_by_category":   result["matched_by_category"],
        "section_feedback":      result["section_feedback"],
        "section_tips":          result["section_tips"],
        "suggestions":           suggestions,
        "created_at":            datetime.utcnow(),
    }
    analysis_id = AnalysisModel.save(db, analysis_doc)

    return redirect(url_for("result", analysis_id=str(analysis_id)))


# ---------------------------------------------------------------------------
# Result dashboard
# ---------------------------------------------------------------------------
@app.get("/result/<analysis_id>")
def result(analysis_id: str):
    analysis = AnalysisModel.find_by_id(db, analysis_id)
    if not analysis:
        flash("Analysis not found.", "error")
        return redirect(url_for("analyzer"))

    return render_template(
        "result.html",
        analysis=analysis,
        is_owner=True, # Everyone can view their own result link
        is_pro=True,   # Make it free/pro for everyone
    )


# ===========================================================================
# PDF REPORT
# ===========================================================================

@app.get("/report/<analysis_id>")
def download_report(analysis_id: str):
    analysis = AnalysisModel.find_by_id(db, analysis_id)
    if not analysis:
        flash("Analysis not found.", "error")
        return redirect(url_for("analyzer"))

    user_name = "Guest"

    try:
        pdf_path = generate_pdf_report(analysis, user_name)
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"ats_report_{analysis_id[:8]}.pdf",
            mimetype="application/pdf",
        )
    except Exception as e:
        flash(f"PDF generation failed: {e}", "error")
        return redirect(url_for("result", analysis_id=analysis_id))


# ===========================================================================
# REWRITE ASSISTANT (JSON endpoint)
# ===========================================================================

@app.post("/rewrite")
def rewrite():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided."}), 400

    use_ai = True # Free AI rewrite for everyone

    improved = rewrite_with_openai(text) if use_ai else rewrite_bullet(text)
    return jsonify({"original": text, "improved": improved, "used_ai": use_ai})


# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    print(f"🚀  ResumeAI running on http://localhost:{port}")
    app.run(debug=debug, port=port)