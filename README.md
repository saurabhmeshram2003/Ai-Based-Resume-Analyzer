# ResumeAI — AI-Powered ATS Resume Analyzer

A production-ready, full-stack SaaS resume analyzer built with **Python Flask**, **MongoDB**, **spaCy NLP**, **Tailwind CSS**, and **Chart.js**.

---

## Features

| Feature | Description |
|---|---|
| 🎯 ATS Score | Weighted 5-dimension scoring (skill match, keyword density, experience, structure) |
| 💡 Skill Gap Analysis | 230+ skills tracked, matched/missing with priority badges |
| 📋 Section Inspector | Checks 6 resume sections with per-section optimization tips |
| ✍️ Bullet Rewriter | Rule-based rewriter; GPT-4o-mini with `OPENAI_API_KEY` |
| 📊 History Dashboard | Chart.js score trend, filters, delete |
| 📄 PDF Reports | ReportLab professional PDF download |
| 🔐 Authentication | Flask-Login + bcrypt, 30-day sessions |
| 👑 Admin Dashboard | User management, charts, subscription control |
| 💳 Subscription Tiers | Free / Pro / Recruiter with mock upgrade |
| 🌙 Dark Mode | Toggle with localStorage persistence |

---

## Project Structure

```
ai_resume_analyzer/
├── app.py                  # Main Flask app (all routes)
├── skills.py               # 230+ skills by category
├── requirements.txt
├── .env                    # Environment variables (copy from .env.example)
├── utils/
│   ├── file_parser.py      # PDF / DOCX extraction
│   ├── text_processor.py   # spaCy NLP helpers
│   ├── scorer.py           # ATS scoring algorithm
│   ├── suggestions.py      # Rule-based + OpenAI suggestion engine
│   └── pdf_report.py       # ReportLab PDF generator
├── models/
│   ├── user.py             # User model + Flask-Login adapter
│   ├── analysis.py         # Analysis model
│   └── subscription.py     # Subscription tier definitions
├── templates/
│   ├── base.html           # Shared nav + footer layout
│   ├── index.html          # Landing page
│   ├── analyzer.html       # File upload + JD input
│   ├── result.html         # Full results dashboard
│   ├── history.html        # Analysis history + Chart.js trend
│   ├── login.html
│   ├── signup.html
│   ├── profile.html        # Edit profile + plan upgrade
│   └── admin.html          # Admin metrics, user & analysis tables
├── static/
│   ├── style.css           # Glassmorphism design system
│   └── script.js           # Frontend: dark mode, drag-drop, gauge, charts
└── uploads/                # Temp storage (files deleted after parsing)
```

---

## Quick Start

### 1. Clone / navigate to the project

```bash
cd "Ai Based Resume Analyzer"
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate.bat       # Windows
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Download the spaCy language model

```bash
python -m spacy download en_core_web_sm
```

### 5. Set up MongoDB

**Option A — Local MongoDB (recommended for dev):**
```bash
# macOS
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

**Option B — MongoDB Atlas (cloud):**
- Create a free cluster at https://cloud.mongodb.com
- Get your connection string and set it in `.env`

### 6. Configure environment variables

```bash
cp .env .env.local    # or just edit .env directly
```

Edit `.env`:
```
SECRET_KEY=your-random-secret-key-here
MONGO_URI=mongodb://localhost:27017        # or Atlas URI
ADMIN_EMAIL=admin@resumeai.com
ADMIN_PASSWORD=Admin@123
OPENAI_API_KEY=                            # optional
```

### 7. Run the app

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## Default Admin Account

On first startup, an admin account is auto-created:

| Field | Value |
|---|---|
| Email | `admin@resumeai.com` |
| Password | `Admin@123` |
| Role | admin |
| Plan | pro |

Log in at `/login` to access the admin dashboard at `/admin`.

---

## Scoring Algorithm

The composite ATS score is computed as:

```
Score = (SkillMatch × 0.40) + (KeywordDensity × 0.20) + (Experience × 0.20) + (Structure × 0.20)
```

| Dimension | Weight | Logic |
|---|---|---|
| **Skill Match** | 40% | `matched_skills / total_jd_skills × 100` |
| **Keyword Density** | 20% | JD meaningful words found in resume / total JD words |
| **Experience** | 20% | 100 if resume contains `N+ years` or senior title, else 50 |
| **Structure** | 20% | Present sections / 6 × 100 (Contact, Summary, Experience, Education, Skills, Projects) |

---

## Subscription Tiers

| Feature | Free | Pro | Recruiter |
|---|---|---|---|
| Analyses/day | 3 | ∞ | ∞ |
| PDF Reports | ✗ | ✓ | ✓ |
| AI Bullet Rewriter | ✗ | ✓ | ✓ |
| Score History | ✓ | ✓ | ✓ |
| Bulk Upload | ✗ | ✗ | ✓ |
| CSV Export | ✗ | ✗ | ✓ |

Use the **mock upgrade** button on `/profile` to change plans during development.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Landing page |
| GET | `/analyzer` | Analyzer tool |
| POST | `/analyze` | Process resume (rate-limited: 10/min) |
| GET | `/result/<id>` | Results dashboard |
| GET | `/history` | User history (auth required) |
| GET | `/api/history` | History JSON |
| DELETE | `/api/analysis/<id>` | Delete analysis |
| GET | `/report/<id>` | Download PDF |
| POST | `/rewrite` | Bullet point rewrite (JSON) |
| GET/POST | `/login` | Authentication |
| GET/POST | `/signup` | Registration |
| GET | `/logout` | Sign out |
| GET/POST | `/profile` | User profile |
| POST | `/upgrade` | Mock plan upgrade |
| GET | `/admin` | Admin dashboard (admin only) |
| POST | `/admin/update-user` | Update user plan (admin only) |

---

## Deployment

### Render / Railway (free tier)

1. Push to GitHub
2. Connect repo to Render / Railway
3. Set environment variables in the dashboard
4. Set start command: `gunicorn app:app`
5. Add `gunicorn` to `requirements.txt`

### Environment Variables Required in Production

```
SECRET_KEY=<random-256-bit-key>
MONGO_URI=<mongodb+srv://...>
OPENAI_API_KEY=<optional>
FLASK_ENV=production
FLASK_DEBUG=0
```

---

## Tech Stack

- **Backend**: Python 3.11+, Flask 3.0, Flask-Login, Flask-Limiter
- **Database**: MongoDB 7.x, pymongo
- **NLP**: spaCy `en_core_web_sm`
- **File Parsing**: pdfplumber, docx2txt
- **PDF Generation**: ReportLab 4.x
- **Frontend**: Tailwind CSS CDN, Chart.js 4, Font Awesome 6
- **Auth**: bcrypt password hashing, secure sessions

---

## License

MIT License — feel free to use, modify, and deploy.
# Ai-Based-Resume-Analyzer
