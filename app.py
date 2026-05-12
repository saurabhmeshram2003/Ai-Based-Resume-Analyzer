"""
ResumeAI — Main Flask Application
Full SaaS resume analyzer with auth, MongoDB, ATS scoring, PDF reports, admin dashboard.
"""
import os
import uuid
import mimetypes
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, request, redirect, url_for,
    jsonify, session, flash, send_file, abort
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient
from bson import ObjectId
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
# Flask-Login
# ---------------------------------------------------------------------------
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"

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
from models.user         import UserModel, FlaskLoginUser
from models.analysis     import AnalysisModel
from models.subscription import SubscriptionModel
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
# Flask-Login loader
# ---------------------------------------------------------------------------
@login_manager.user_loader
def load_user(user_id: str):
    user_doc = UserModel.find_by_id(db, user_id)
    if user_doc:
        return FlaskLoginUser(user_doc)
    return None


# ---------------------------------------------------------------------------
# Admin seed
# ---------------------------------------------------------------------------
def seed_admin():
    """Auto-create an admin account on startup if it doesn't exist."""
    email = os.getenv("ADMIN_EMAIL", "admin@resumeai.com")
    pwd   = os.getenv("ADMIN_PASSWORD", "Admin@123")
    if not UserModel.find_by_email(db, email):
        UserModel.create(db, {
            "name": "Admin", "email": email,
            "password": pwd, "role": "admin", "subscription": "pro",
        })
        print(f"✅  Admin seeded → {email}  /  {pwd}")


with app.app_context():
    try:
        seed_admin()
    except Exception as e:
        print(f"⚠️  Could not seed admin (MongoDB not available?): {e}")


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


def check_free_limit() -> bool:
    """Returns True if the anonymous user may still analyze today."""
    today = datetime.utcnow().date().isoformat()
    if session.get("daily_date") != today:
        session["daily_date"]  = today
        session["daily_count"] = 0
    return session.get("daily_count", 0) < 3


# ---------------------------------------------------------------------------
# Context processor – makes current_user always available in templates
# ---------------------------------------------------------------------------
@app.context_processor
def inject_globals():
    return {
        "current_user": current_user,
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

    # ---- Subscription / daily-limit check --------------------------------
    if current_user.is_authenticated:
        plan      = current_user.subscription
        daily_used = AnalysisModel.daily_count_for_user(db, current_user.id)
        if not SubscriptionModel.can_analyze(plan, daily_used):
            flash("You've reached today's analysis limit. Upgrade to Pro for unlimited analyses.", "warning")
            return redirect(url_for("profile"))
    else:
        if not check_free_limit():
            flash("Free daily limit reached (3/day). Sign up for unlimited access.", "warning")
            return redirect(url_for("signup"))

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
        "user_id":               ObjectId(current_user.id) if current_user.is_authenticated else None,
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

    # ---- Update anonymous counter ----------------------------------------
    if not current_user.is_authenticated:
        session["daily_count"] = session.get("daily_count", 0) + 1

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

    # Determine if logged-in user owns this analysis (for save button)
    is_owner = (
        current_user.is_authenticated
        and analysis.get("user_id") == current_user.id
    )
    is_pro = current_user.is_authenticated and current_user.is_pro

    return render_template(
        "result.html",
        analysis=analysis,
        is_owner=is_owner,
        is_pro=is_pro,
    )


# ---------------------------------------------------------------------------
# History dashboard
# ---------------------------------------------------------------------------
@app.get("/history")
@login_required
def history():
    analyses = AnalysisModel.find_by_user(db, current_user.id)
    return render_template("history.html", analyses=analyses)


@app.get("/api/history")
@login_required
def api_history():
    analyses = AnalysisModel.find_by_user(db, current_user.id)
    return jsonify([{
        "id":       a["_id"],
        "filename": a["filename"],
        "job_role": a.get("job_role", "General"),
        "score":    a["score"],
        "date":     a["created_at"].isoformat() if hasattr(a.get("created_at"), "isoformat") else str(a.get("created_at", "")),
    } for a in analyses])


@app.delete("/api/analysis/<analysis_id>")
@login_required
def delete_analysis(analysis_id: str):
    deleted = AnalysisModel.delete(db, analysis_id, current_user.id)
    return jsonify({"success": deleted}), (200 if deleted else 403)


# ===========================================================================
# AUTH ROUTES
# ===========================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("analyzer"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        user_doc = UserModel.find_by_email(db, email)
        if user_doc and UserModel.verify_password(user_doc, password):
            flask_user = FlaskLoginUser(user_doc)
            login_user(flask_user, remember=remember, duration=timedelta(days=30))
            flash(f"Welcome back, {flask_user.name}! 👋", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("analyzer"))
        else:
            flash("Invalid email or password.", "error")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("analyzer"))

    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        errors = []
        if not all([name, email, password, confirm]):
            errors.append("All fields are required.")
        elif password != confirm:
            errors.append("Passwords do not match.")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        elif UserModel.find_by_email(db, email):
            errors.append("An account with this email already exists.")

        if errors:
            for err in errors:
                flash(err, "error")
        else:
            uid = UserModel.create(db, {
                "name": name, "email": email,
                "password": password, "role": "user", "subscription": "free",
            })
            user_doc = UserModel.find_by_id(db, str(uid))
            login_user(FlaskLoginUser(user_doc))
            flash("Account created! Let's analyze your first resume. 🚀", "success")
            return redirect(url_for("analyzer"))

    return render_template("signup.html")


@app.get("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been signed out.", "info")
    return redirect(url_for("index"))


# ===========================================================================
# USER PROFILE
# ===========================================================================

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        target_roles = request.form.getlist("target_roles")
        update = {
            "name":                    request.form.get("name", current_user.name).strip(),
            "profile.yoe":             int(request.form.get("yoe", 0) or 0),
            "profile.industry":        request.form.get("industry", "").strip(),
            "profile.target_roles":    target_roles,
        }
        UserModel.update(db, current_user.id, update)
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))

    user_doc        = UserModel.find_by_id(db, current_user.id)
    recent_analyses = AnalysisModel.find_by_user(db, current_user.id, limit=5)
    plan_info       = SubscriptionModel.get_limits(current_user.subscription)
    daily_used      = AnalysisModel.daily_count_for_user(db, current_user.id)

    return render_template(
        "profile.html",
        user=user_doc,
        recent_analyses=recent_analyses,
        plan_info=plan_info,
        daily_used=daily_used,
        job_roles=JOB_ROLES,
    )


@app.post("/upgrade")
@login_required
def upgrade():
    plan = request.form.get("plan", "pro")
    if plan in ("pro", "recruiter", "free"):
        UserModel.update_subscription(db, current_user.id, plan)
        flash(f"🎉 Plan changed to {plan.title()}! Enjoy your new features.", "success")
    return redirect(url_for("profile"))


# ===========================================================================
# ADMIN DASHBOARD
# ===========================================================================

@app.get("/admin")
@login_required
def admin():
    if not current_user.is_admin:
        flash("Access denied.", "error")
        return redirect(url_for("index"))

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Metrics
    total_users     = db.users.count_documents({})
    daily_analyses  = db.analyses.count_documents({"created_at": {"$gte": today}})
    pro_users       = db.users.count_documents({"subscription": {"$in": ["pro", "recruiter"]}})

    avg_pipeline    = [{"$group": {"_id": None, "avg": {"$avg": "$score"}}}]
    avg_result      = list(db.analyses.aggregate(avg_pipeline))
    avg_score       = round(avg_result[0]["avg"], 1) if avg_result else 0

    # Top roles
    role_pipeline   = [
        {"$group": {"_id": "$job_role", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}, {"$limit": 6},
    ]
    top_roles       = list(db.analyses.aggregate(role_pipeline))

    users           = UserModel.get_all(db, limit=50)
    analyses        = AnalysisModel.get_all(db, limit=50)

    metrics = {
        "total_users":    total_users,
        "daily_analyses": daily_analyses,
        "avg_score":      avg_score,
        "pro_users":      pro_users,
        "top_roles":      top_roles,
    }

    return render_template("admin.html", metrics=metrics, users=users, analyses=analyses)


@app.post("/admin/update-user")
@login_required
def admin_update_user():
    if not current_user.is_admin:
        abort(403)
    user_id = request.form.get("user_id")
    plan    = request.form.get("plan")
    if user_id and plan in ("free", "pro", "recruiter"):
        UserModel.update_subscription(db, user_id, plan)
        flash(f"User subscription updated to {plan.title()}.", "success")
    return redirect(url_for("admin"))


# ===========================================================================
# PDF REPORT
# ===========================================================================

@app.get("/report/<analysis_id>")
def download_report(analysis_id: str):
    analysis = AnalysisModel.find_by_id(db, analysis_id)
    if not analysis:
        flash("Analysis not found.", "error")
        return redirect(url_for("analyzer"))

    user_name = current_user.name if current_user.is_authenticated else "Guest"

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

    use_ai = (
        current_user.is_authenticated
        and SubscriptionModel.can_use_ai_rewrite(current_user.subscription)
    )

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