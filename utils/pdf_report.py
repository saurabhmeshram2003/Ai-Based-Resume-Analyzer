"""
PDF Report Generator using ReportLab.
Produces a professional ATS analysis report as a downloadable PDF.
"""
import tempfile
import os
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
INDIGO   = colors.HexColor("#4f46e5")
EMERALD  = colors.HexColor("#10b981")
AMBER    = colors.HexColor("#f59e0b")
RED      = colors.HexColor("#ef4444")
SLATE_50 = colors.HexColor("#f8fafc")
SLATE_200= colors.HexColor("#e2e8f0")
SLATE_700= colors.HexColor("#334155")
WHITE    = colors.white


def _score_color(score: float):
    if score >= 75:
        return EMERALD
    elif score >= 50:
        return AMBER
    return RED


def _build_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "ReportTitle", parent=base["Normal"],
            fontSize=22, fontName="Helvetica-Bold",
            textColor=INDIGO, spaceAfter=4, alignment=TA_LEFT
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"],
            fontSize=10, textColor=SLATE_700, spaceAfter=2
        ),
        "section_heading": ParagraphStyle(
            "SectionHeading", parent=base["Normal"],
            fontSize=12, fontName="Helvetica-Bold",
            textColor=SLATE_700, spaceBefore=12, spaceAfter=6
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"],
            fontSize=9, textColor=SLATE_700, spaceAfter=4, leading=14
        ),
        "score_big": ParagraphStyle(
            "ScoreBig", parent=base["Normal"],
            fontSize=36, fontName="Helvetica-Bold",
            alignment=TA_CENTER, spaceAfter=2
        ),
        "score_label": ParagraphStyle(
            "ScoreLabel", parent=base["Normal"],
            fontSize=11, alignment=TA_CENTER, spaceAfter=8
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["Normal"],
            fontSize=9, textColor=SLATE_700,
            leftIndent=12, spaceAfter=3, leading=14,
            bulletText="•"
        ),
    }
    return styles


def generate_pdf_report(analysis: dict, user_name: str = "User") -> str:
    """
    Generate a PDF report for the given analysis.
    Returns the path to a temporary PDF file.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.close()

    doc = SimpleDocTemplate(
        tmp.name, pagesize=letter,
        rightMargin=0.75 * inch, leftMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch
    )

    styles = _build_styles()
    story = []

    # ------------------------------------------------------------------ Header
    created_at = analysis.get("created_at")
    date_str = (
        created_at.strftime("%B %d, %Y") if hasattr(created_at, "strftime")
        else str(created_at)[:10]
    )
    story.append(Paragraph("ATS Resume Analysis Report", styles["title"]))
    story.append(Paragraph(f"Prepared for: <b>{user_name}</b>  |  Date: {date_str}", styles["subtitle"]))
    story.append(Paragraph(f"Resume: {analysis.get('filename', 'N/A')}  |  Role: {analysis.get('job_role', 'General')}", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=SLATE_200, spaceAfter=12))

    # ------------------------------------------------------------------ Score
    score = analysis.get("score", 0)
    score_col = _score_color(score)
    score_label = analysis.get("score_label", "")

    score_table = Table(
        [[
            Paragraph(f'<font color="{score_col.hexval()}">{score}%</font>', styles["score_big"]),
            Paragraph(f'<font color="{score_col.hexval()}">{score_label}</font>', styles["score_label"])
        ]],
        colWidths=[1.5 * inch, 5.5 * inch]
    )
    score_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), SLATE_50),
        ("BOX", (0, 0), (-1, -1), 0.5, SLATE_200),
        ("ROUNDEDCORNERS", (0, 0), (-1, -1)),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 12))

    # ------------------------------------------------------------------ Breakdown
    story.append(Paragraph("Score Breakdown", styles["section_heading"]))

    breakdown_data = [
        ["Metric", "Score", "Weight", "Status"],
        ["Skill Match",       f"{analysis.get('skill_match_score', 0):.1f}%",       "40%", ""],
        ["Keyword Density",   f"{analysis.get('keyword_density_score', 0):.1f}%",   "20%", ""],
        ["Experience",        f"{analysis.get('experience_score', 0):.1f}%",        "20%", ""],
        ["Structure/Format",  f"{analysis.get('structure_score', 0):.1f}%",         "20%", ""],
    ]
    # Add status column
    for i in range(1, len(breakdown_data)):
        s = float(breakdown_data[i][1].replace("%", ""))
        breakdown_data[i][3] = "✓ Good" if s >= 70 else "⚠ Improve" if s >= 40 else "✗ Poor"

    breakdown_table = Table(breakdown_data, colWidths=[2.5*inch, 1.5*inch, 1*inch, 1.5*inch])
    breakdown_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), INDIGO),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, SLATE_50]),
        ("GRID",          (0, 0), (-1, -1), 0.4, SLATE_200),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(breakdown_table)
    story.append(Spacer(1, 12))

    # ------------------------------------------------------------------ Matched Skills
    matched = analysis.get("matched_skills", [])
    story.append(Paragraph("Matched Skills", styles["section_heading"]))
    if matched:
        story.append(Paragraph(", ".join(matched), styles["body"]))
    else:
        story.append(Paragraph("No matching skills detected.", styles["body"]))
    story.append(Spacer(1, 6))

    # ------------------------------------------------------------------ Missing Skills
    missing = analysis.get("missing_skills", [])
    story.append(Paragraph("Missing Skills (Add to Resume)", styles["section_heading"]))
    if missing:
        story.append(Paragraph(", ".join(missing[:20]), styles["body"]))
    else:
        story.append(Paragraph("No missing skills — great alignment!", styles["body"]))
    story.append(Spacer(1, 6))

    # ------------------------------------------------------------------ Section Analysis
    story.append(Paragraph("Resume Section Analysis", styles["section_heading"]))
    section_feedback = analysis.get("section_feedback", {})
    tips = analysis.get("section_tips", {})
    section_data = [["Section", "Status", "Recommendation"]]
    for section, present in section_feedback.items():
        status = "✓ Present" if present else "✗ Missing"
        tip = tips.get(section, "—")
        section_data.append([section.title(), status, tip])

    section_table = Table(section_data, colWidths=[1.2*inch, 1*inch, 4.3*inch])
    section_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), SLATE_700),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, SLATE_50]),
        ("GRID",          (0, 0), (-1, -1), 0.4, SLATE_200),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("WORDWRAP",      (2, 1), (2, -1), True),
    ]))
    story.append(section_table)
    story.append(Spacer(1, 12))

    # ------------------------------------------------------------------ Suggestions
    suggestions = analysis.get("suggestions", [])
    story.append(Paragraph("Recommendations", styles["section_heading"]))
    for sug in suggestions:
        text = sug.get("text", str(sug)) if isinstance(sug, dict) else str(sug)
        story.append(Paragraph(text, styles["bullet"]))

    # ------------------------------------------------------------------ Footer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_200))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Generated by <b>ResumeAI</b> — ATS Resume Analyzer  |  resumeai.com",
        ParagraphStyle("Footer", fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    ))

    doc.build(story)
    return tmp.name
