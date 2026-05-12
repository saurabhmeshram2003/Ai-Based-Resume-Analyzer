"""
File parser utility: extracts raw text from PDF and DOCX files.
"""
import pdfplumber
import docx2txt
import os


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from a PDF file using pdfplumber."""
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {e}")
    return text.strip()


def extract_text_from_docx(file_path: str) -> str:
    """Extract all text from a DOCX file using docx2txt."""
    try:
        return docx2txt.process(file_path).strip()
    except Exception as e:
        raise ValueError(f"Failed to parse DOCX: {e}")


def extract_text(file_path: str) -> str:
    """
    Auto-detect file type and extract text.
    Raises ValueError for unsupported formats.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
