"""
Text processing utility: cleans, tokenizes, and extracts entities from resume text.
Uses spaCy for NLP tasks.
"""
import re

# Lazy spaCy load to avoid slow startup when not needed
_nlp = None


def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except Exception:
            _nlp = None
    return _nlp


def clean_text(text: str) -> str:
    """Normalize whitespace and strip control characters."""
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def extract_entities(text: str) -> dict:
    """
    Use spaCy NER to extract named entities (ORGs, dates, GPE, etc.).
    Falls back gracefully if spaCy model is not available.
    """
    nlp = get_nlp()
    if not nlp:
        return {}

    doc = nlp(text[:10000])  # Limit for performance
    entities = {}
    for ent in doc.ents:
        entities.setdefault(ent.label_, []).append(ent.text)
    return entities


def extract_years_experience(text: str) -> int:
    """
    Parse mentions of years of experience from resume text.
    Returns the highest number found, or 0 if none.
    """
    patterns = [
        r'(\d+)\+?\s*years?\s+of\s+experience',
        r'(\d+)\+?\s*years?\s+experience',
        r'experience\s+of\s+(\d+)\+?\s*years?',
        r'(\d+)\+?\s*yrs?\s+of\s+experience',
    ]
    years = []
    text_lower = text.lower()
    for p in patterns:
        matches = re.findall(p, text_lower)
        years.extend(int(m) for m in matches)
    return max(years) if years else 0


def count_action_verbs(text: str) -> int:
    """Count strong action verbs in resume text."""
    action_verbs = [
        "developed", "architected", "led", "built", "optimized", "implemented",
        "engineered", "designed", "deployed", "automated", "created", "launched",
        "delivered", "managed", "established", "improved", "reduced", "increased",
        "accelerated", "transformed", "spearheaded", "pioneered", "streamlined",
        "mentored", "collaborated", "coordinated", "executed", "generated",
    ]
    text_lower = text.lower()
    return sum(1 for verb in action_verbs if verb in text_lower)


def has_quantified_results(text: str) -> bool:
    """Check if resume contains measurable/quantified results."""
    pattern = r'(\d+\s*%|\d+x|\$[\d,]+|\d+\s*(million|billion|thousand|k\b|m\b))'
    return bool(re.search(pattern, text.lower()))
