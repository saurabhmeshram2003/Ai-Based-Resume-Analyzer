"""
ATS Scoring Engine.
Computes a weighted composite ATS score from:
  - Skill match (40%)
  - Keyword density (20%)
  - Experience score (20%)
  - Structure/formatting score (20%)
"""
import re
import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from skills import SKILLS_BY_CATEGORY, SKILLS_FLAT_SORTED


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------
SECTION_PATTERNS = {
    "contact":    r'email|phone|mobile|linkedin|github|contact\s*info|address',
    "summary":    r'\b(summary|objective|profile|about\s+me|professional\s+summary)\b',
    "experience": r'\b(experience|work\s+history|employment|professional\s+background|career)\b',
    "education":  r'\b(education|degree|university|college|school|academic)\b',
    "skills":     r'\b(skills|technologies|competencies|expertise|proficiencies|tech\s+stack)\b',
    "projects":   r'\b(projects|portfolio|personal\s+projects|open[\s-]source)\b',
}

SENIOR_TITLE_PATTERN = r'\b(senior|sr\.|lead|principal|staff|architect|head|director|vp|chief)\b'


def check_structure(text: str) -> dict:
    """Check presence of key resume sections."""
    text_lower = text.lower()
    return {
        section: bool(re.search(pattern, text_lower))
        for section, pattern in SECTION_PATTERNS.items()
    }


def get_section_tips(section_feedback: dict) -> dict:
    """Return optimization tips for each section."""
    TIPS = {
        "contact":    "Include email, phone number, LinkedIn, and GitHub links.",
        "summary":    "Add a 2-3 sentence professional summary tailored to the role.",
        "experience": "List work experience in reverse chronological order with bullet points.",
        "education":  "Include your degree, institution, and graduation year.",
        "skills":     "Create a dedicated skills section with your top technologies.",
        "projects":   "Add 2-3 key projects with tech stack, impact, and GitHub links.",
    }
    return {section: TIPS[section] for section in section_feedback}


# ---------------------------------------------------------------------------
# Skill extraction
# ---------------------------------------------------------------------------
def extract_skills_flat(text: str) -> set:
    """Return all known skills found in text (greedy, longest match first)."""
    text_lower = text.lower()
    found = set()
    for skill in SKILLS_FLAT_SORTED:
        # word-boundary safe match
        pattern = r'(?<![a-z0-9])' + re.escape(skill) + r'(?![a-z0-9])'
        if re.search(pattern, text_lower):
            found.add(skill)
    return found


def extract_skills_by_category(text: str) -> dict:
    """Return matched skills grouped by category."""
    text_lower = text.lower()
    result = {}
    for category, skills in SKILLS_BY_CATEGORY.items():
        matched = []
        for skill in skills:
            pattern = r'(?<![a-z0-9])' + re.escape(skill) + r'(?![a-z0-9])'
            if re.search(pattern, text_lower):
                matched.append(skill)
        if matched:
            result[category] = matched
    return result


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------
def compute_score(resume_text: str, jd_text: str) -> dict:
    """
    Full ATS scoring pipeline.
    Returns a dict with all scores, matched/missing skills, section feedback, etc.
    """
    # --- Skill match (40%) ---
    resume_skills = extract_skills_flat(resume_text)
    jd_skills = extract_skills_flat(jd_text)

    matched_skills = sorted(resume_skills & jd_skills)
    missing_skills = sorted(jd_skills - resume_skills)

    skill_match_score = round((len(matched_skills) / max(len(jd_skills), 1)) * 100, 1)

    # --- Keyword density (20%) ---
    # Use meaningful words (length > 4) from the JD
    jd_words = re.findall(r'\b[a-z]{4,}\b', jd_text.lower())
    resume_lower = resume_text.lower()
    hits = sum(1 for w in set(jd_words) if w in resume_lower)
    keyword_density_score = round(min((hits / max(len(set(jd_words)), 1)) * 100, 100), 1)

    # --- Experience score (20%) ---
    has_years = bool(re.search(
        r'\d+\+?\s*years?\s+(of\s+)?(experience|exp\.?)|senior|lead|principal|architect',
        resume_text.lower()
    ))
    experience_score = 100.0 if has_years else 50.0

    # --- Structure / formatting score (20%) ---
    section_feedback = check_structure(resume_text)
    structure_score = round((sum(section_feedback.values()) / len(section_feedback)) * 100, 1)

    # --- Final weighted score ---
    final_score = round(
        skill_match_score * 0.40 +
        keyword_density_score * 0.20 +
        experience_score * 0.20 +
        structure_score * 0.20,
        1
    )
    final_score = max(0.0, min(100.0, final_score))

    # --- Missing skills with priority ---
    missing_with_priority = []
    for skill in missing_skills[:20]:
        count = jd_text.lower().count(skill)
        priority = "high" if count >= 2 else "medium"
        missing_with_priority.append({"skill": skill, "priority": priority})

    # --- Score label ---
    if final_score >= 75:
        label = "Excellent"
        label_color = "green"
    elif final_score >= 55:
        label = "Good"
        label_color = "yellow"
    elif final_score >= 35:
        label = "Fair"
        label_color = "orange"
    else:
        label = "Poor"
        label_color = "red"

    return {
        "score": final_score,
        "score_label": label,
        "score_color": label_color,
        "skill_match_score": skill_match_score,
        "keyword_density_score": keyword_density_score,
        "experience_score": experience_score,
        "structure_score": structure_score,
        "formatting_score": structure_score,  # alias
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "missing_skills_with_priority": missing_with_priority,
        "matched_by_category": extract_skills_by_category(resume_text),
        "section_feedback": section_feedback,
        "section_tips": get_section_tips(section_feedback),
    }
