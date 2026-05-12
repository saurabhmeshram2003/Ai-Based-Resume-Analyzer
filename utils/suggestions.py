"""
Suggestion engine: generates actionable, rule-based resume improvement tips.
Also provides AI-powered and rule-based bullet point rewriting.
"""
import re
import os

ACTION_VERBS = [
    "developed", "architected", "led", "built", "optimized", "implemented",
    "engineered", "designed", "deployed", "automated", "created", "launched",
    "delivered", "managed", "improved", "reduced", "increased", "spearheaded",
    "streamlined", "mentored", "executed", "transformed"
]

WEAK_VERBS = [
    "did", "made", "helped", "worked", "used", "was responsible",
    "participated", "assisted", "supported", "handled"
]

PRIORITY_ICONS = {
    "high":   "fa-circle-exclamation",
    "medium": "fa-circle-info",
    "low":    "fa-circle-minus",
}

PRIORITY_COLORS = {
    "high":   "red",
    "medium": "yellow",
    "low":    "blue",
}


def generate_suggestions(result: dict) -> list:
    """
    Generate a list of actionable suggestion dicts from a scorer result.
    Each dict: { type, priority, icon, color, text }
    """
    suggestions = []

    # 1. Missing skills
    missing = result.get("missing_skills", [])
    if missing:
        top = missing[:8]
        suggestions.append({
            "type": "skills",
            "priority": "high",
            "icon": "fa-puzzle-piece",
            "color": "red",
            "text": f"Add these key skills to your resume: {', '.join(top)}."
        })

    # 2. Keyword density
    kd = result.get("keyword_density_score", 100)
    if kd < 50:
        suggestions.append({
            "type": "keywords",
            "priority": "high",
            "icon": "fa-magnifying-glass",
            "color": "red",
            "text": "Include more keywords from the job description. Mirror their exact phrasing for better ATS parsing."
        })
    elif kd < 70:
        suggestions.append({
            "type": "keywords",
            "priority": "medium",
            "icon": "fa-magnifying-glass",
            "color": "yellow",
            "text": "Increase keyword density slightly by adding JD-specific terms naturally throughout your resume."
        })

    # 3. Quantified results check
    has_metrics = bool(re.search(
        r'(\d+\s*%|\d+x|\$[\d,]+|\d+\s*(million|billion|thousand))',
        result.get("resume_text_sample", ""),
        re.IGNORECASE
    ))
    if not has_metrics:
        suggestions.append({
            "type": "metrics",
            "priority": "medium",
            "icon": "fa-chart-line",
            "color": "yellow",
            "text": "Quantify your achievements. Example: 'Reduced API latency by 40%', 'Managed a team of 8 engineers', 'Increased revenue by $1.2M'."
        })

    # 4. Action verbs
    sample = result.get("resume_text_sample", "").lower()
    if sample and not any(v in sample for v in ACTION_VERBS):
        suggestions.append({
            "type": "verbs",
            "priority": "medium",
            "icon": "fa-bolt",
            "color": "yellow",
            "text": f"Use strong action verbs to open each bullet point: {', '.join(ACTION_VERBS[:8])}."
        })

    # 5. Missing sections
    section_feedback = result.get("section_feedback", {})
    missing_sections = [s for s, present in section_feedback.items() if not present]
    for section in missing_sections:
        tip = result.get("section_tips", {}).get(section, f"Add a {section.title()} section.")
        suggestions.append({
            "type": "structure",
            "priority": "low",
            "icon": "fa-layer-group",
            "color": "blue",
            "text": tip
        })

    # 6. Experience
    exp = result.get("experience_score", 100)
    if exp < 100:
        suggestions.append({
            "type": "experience",
            "priority": "medium",
            "icon": "fa-briefcase",
            "color": "yellow",
            "text": "Mention your years of experience explicitly. E.g., '5+ years of experience in backend development'."
        })

    # 7. Generic ATS tip (always include)
    suggestions.append({
        "type": "format",
        "priority": "low",
        "icon": "fa-file-lines",
        "color": "blue",
        "text": "Use a clean, single-column layout. Avoid tables, headers/footers, and graphics that ATS parsers cannot read."
    })

    return suggestions


# ---------------------------------------------------------------------------
# Bullet point rewriter
# ---------------------------------------------------------------------------
def rewrite_bullet(text: str) -> str:
    """Rule-based bullet point improver (fallback when OpenAI key is absent)."""
    text = text.strip().rstrip(".")
    if not text:
        return text

    # Remove weak verb starters
    for weak in WEAK_VERBS:
        pattern = r'^' + re.escape(weak) + r'[\s,]+?'
        text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()

    # Capitalize
    if text:
        text = text[0].upper() + text[1:]

    # Add strong verb if first word is not an action verb
    first_word = text.split()[0].lower() if text.split() else ""
    if first_word not in [v.lower() for v in ACTION_VERBS]:
        text = f"Developed and implemented {text[0].lower()}{text[1:]}"

    # Add metrics if none present
    if not re.search(r'\d+', text):
        text = f"{text}, resulting in a measurable improvement in efficiency and team output"

    return text + "."


def rewrite_with_openai(text: str) -> str:
    """
    GPT-4o-mini powered bullet point rewrite.
    Falls back to rule-based rewrite if API key is absent or call fails.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return rewrite_bullet(text)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional resume writer specializing in tech resumes. "
                        "Rewrite the given resume bullet point to be more impactful: "
                        "start with a strong action verb, include a quantifiable result, "
                        "and make it ATS-friendly. Return ONLY the rewritten bullet point, "
                        "no explanations or quotation marks."
                    )
                },
                {"role": "user", "content": text}
            ],
            max_tokens=120,
            temperature=0.7
        )
        improved = response.choices[0].message.content.strip()
        return improved if improved else rewrite_bullet(text)
    except Exception:
        return rewrite_bullet(text)
