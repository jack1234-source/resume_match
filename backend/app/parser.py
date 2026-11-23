"""Document extraction and lightweight, explainable resume/JD field extraction."""
from __future__ import annotations
import re
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

from docx import Document
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_BYTES = 10 * 1024 * 1024

# Canonical skill -> common spellings. This is intentionally small and editable;
# expand it for the roles your recruiter prototype needs to support.
SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Java": ("java",),
    "Python": ("python",),
    "C++": ("c++", "cpp"),
    "C#": ("c#", "c sharp"),
    "JavaScript": ("javascript", "js"),
    "TypeScript": ("typescript", "ts"),
    "SQL": ("sql", "structured query language"),
    "PostgreSQL": ("postgresql", "postgres"),
    "MySQL": ("mysql",),
    "MongoDB": ("mongodb", "mongo db"),
    "Redis": ("redis",),
    "Spring Boot": ("spring boot", "springboot"),
    "Spring": ("spring framework",),
    "Django": ("django",),
    "Flask": ("flask",),
    "FastAPI": ("fastapi", "fast api"),
    "React": ("react.js", "reactjs", "react"),
    "Angular": ("angular",),
    "Node.js": ("node.js", "nodejs", "node js"),
    "Express": ("express.js", "expressjs", "express"),
    "HTML": ("html5", "html"),
    "CSS": ("css3", "css"),
    "Docker": ("docker",),
    "Kubernetes": ("kubernetes", "k8s"),
    "AWS": ("amazon web services", "aws"),
    "Azure": ("microsoft azure", "azure"),
    "GCP": ("google cloud platform", "gcp"),
    "CI/CD": ("ci/cd", "continuous integration", "continuous delivery"),
    "Git": ("git", "github", "gitlab"),
    "Linux": ("linux",),
    "REST API": ("rest api", "restful api", "rest services"),
    "GraphQL": ("graphql",),
    "Microservices": ("microservices", "micro services"),
    "Machine Learning": ("machine learning", "ml"),
    "Deep Learning": ("deep learning",),
    "NLP": ("natural language processing", "nlp"),
    "TensorFlow": ("tensorflow",),
    "PyTorch": ("pytorch", "torch"),
    "Scikit-learn": ("scikit-learn", "sklearn"),
    "Pandas": ("pandas",),
    "NumPy": ("numpy",),
    "Data Structures": ("data structures", "dsa"),
    "Algorithms": ("algorithms",),
    "Selenium": ("selenium",),
    "Jest": ("jest",),
    "Postman": ("postman",),
    "Agile": ("agile", "scrum"),
}


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def extract_document_text(filename: str, content: bytes) -> str:
    """Extract text from PDF or DOCX bytes; reject unsupported/empty files."""
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("File exceeds the 10 MB upload limit.")
    if not content:
        raise ValueError("The uploaded file is empty.")

    filename = str(filename or "").strip().replace("\\", "/").rsplit("/", 1)[-1]
    suffix = Path(filename).suffix.lower()
    if b"%PDF-" in content[:1024]:
        suffix = ".pdf"
    else:
        try:
            with ZipFile(BytesIO(content)) as archive:
                entries = set(archive.namelist())
            if "[Content_Types].xml" in entries and "word/document.xml" in entries:
                suffix = ".docx"
        except (BadZipFile, OSError):
            pass
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Only PDF and DOCX files are supported (received {filename or 'unnamed file'}).")

    try:
        if suffix == ".pdf":
            reader = PdfReader(BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages)
        else:
            document = Document(BytesIO(content))
            parts = [p.text for p in document.paragraphs if p.text.strip()]
            for table in document.tables:
                for row in table.rows:
                    parts.append(" | ".join(cell.text for cell in row.cells))
            text = "\n".join(parts)
    except Exception as exc:
        raise ValueError(f"Could not read {suffix.upper()} file: {exc}") from exc

    text = text.strip()
    if len(text) < 20:
        raise ValueError("No readable text found. Scanned/image-only PDFs need OCR before upload.")
    return text


def extract_skills(text: str) -> list[str]:
    lower = (text or "").lower()
    found: list[str] = []
    for canonical, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            # Avoid partial matches such as 'git' inside 'digital'.
            pattern = rf"(?<![a-z0-9+#]){re.escape(alias)}(?![a-z0-9+#])"
            if re.search(pattern, lower):
                found.append(canonical)
                break
    return found


def extract_experience_years(text: str) -> float | None:
    """Prefer explicit years-of-experience statements, otherwise sum date ranges."""
    lower = text.lower()
    patterns = [
        r"(?:over|more than)\s+(\d+(?:\.\d+)?)\s*\+?\s+years?",
        r"(\d+(?:\.\d+)?)\s*\+?\s+years?\s+(?:of\s+)?(?:professional\s+)?(?:work\s+)?experience",
        r"experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*\+?\s+years?",
    ]
    patterns.append(r"(\d+(?:\.\d+)?)\s*\+?\s+years?\b[^.\n]{0,80}\bexperience\b")
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            return round(float(match.group(1)), 1)

    # Fallback: take the earliest and latest year mentioned in employment-like
    # date ranges. It is deliberately conservative and capped at 40 years.
    date_range = re.findall(
        r"\b(19\d{2}|20\d{2})\s*(?:-|–|to)\s*(present|current|19\d{2}|20\d{2})\b",
        lower,
    )
    if date_range:
        current_year = date.today().year
        intervals = []
        for start, end in date_range:
            s = int(start)
            e = current_year if end in {"present", "current"} else int(end)
            if e >= s:
                intervals.append((s, e))
        if intervals:
            # Merge overlapping year intervals to avoid double-counting concurrent roles.
            intervals.sort()
            merged = []
            for start, end in intervals:
                if not merged or start > merged[-1][1]:
                    merged.append([start, end])
                else:
                    merged[-1][1] = max(merged[-1][1], end)
            return round(min(40.0, sum(end - start for start, end in merged)), 1)
    return None


EDUCATION_LEVELS: list[tuple[str, int, tuple[str, ...]]] = [
    (
        "PhD",
        5,
        (r"ph\.?d\.?", r"doctorate", r"doctoral"),
    ),
    (
        "Master's",
        4,
        (
            r"master(?:'s)?",
            r"masters",
            r"m\.?tech",
            r"m\.e\.?",
            r"m\.?sc\.?",
            r"msc",
            r"mca",
            r"mba",
            r"post[\s-]graduate",
        ),
    ),
    (
        "Bachelor's",
        3,
        (
            r"bachelor(?:'s)?",
            r"bachelors",
            r"b\.?tech",
            r"b\.e\.?",
            r"b\.?sc\.?",
            r"bsc",
            r"bca",
            r"undergraduate",
        ),
    ),
    (
        "Diploma",
        2,
        (r"diploma",),
    ),
]


def extract_education(text: str) -> dict[str, Any]:
    lower = (text or "").lower()
    for label, rank, patterns in EDUCATION_LEVELS:
        for pattern in patterns:
            regex = rf"(?<![a-z0-9]){pattern}(?![a-z0-9])"
            if re.search(regex, lower):
                return {"level": label, "rank": rank}
    return {"level": None, "rank": 0}


def extract_contact(text: str) -> dict[str, str | None]:
    email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)
    phone_candidates = re.findall(r"(?:\+?\d[\d\s().-]{8,}\d)", text)
    phone = next((candidate for candidate in phone_candidates if len(re.sub(r"\D", "", candidate)) >= 10), None)
    return {
        "email": email_match.group(0) if email_match else None,
        "phone": _normalise(phone) if phone else None,
    }


def extract_candidate_name(text: str, filename: str) -> str:
    ignored = {"resume", "curriculum vitae", "cv", "profile", "contact", "professional summary"}
    for line in text.splitlines()[:12]:
        clean = _normalise(re.sub(r"[|•·]", " ", line))
        if not clean or clean.lower() in ignored or "@" in clean or re.search(r"\d{5,}", clean):
            continue
        if len(clean) <= 70 and len(clean.split()) <= 5 and not any(
            word in clean.lower() for word in ("experience", "engineer", "developer", "skills", "education")
        ):
            return clean
    return Path(filename).stem.replace("_", " ").replace("-", " ").title()


def parse_resume(text: str, filename: str) -> dict[str, Any]:
    contact = extract_contact(text)
    return {
        "name": extract_candidate_name(text, filename),
        **contact,
        "experience_years": extract_experience_years(text),
        "skills": extract_skills(text),
        "education": extract_education(text),
        "summary": _normalise(text)[:500],
    }


def parse_job_description(text: str) -> dict[str, Any]:
    all_skills = extract_skills(text)
    lines = [line.strip(" \t-*•") for line in text.splitlines() if line.strip()]
    preferred_lines = [
        line for line in lines
        if re.search(r"\b(preferred|nice[- ]to[- ]have|good[- ]to[- ]have|bonus|desirable)\b", line, re.I)
    ]
    required_lines = [line for line in lines if line not in preferred_lines]
    preferred_found = extract_skills("\n".join(preferred_lines))
    required_skills = extract_skills("\n".join(required_lines))
    # A skill mentioned in a required section remains required even if it is repeated as preferred.
    preferred_skills = [skill for skill in preferred_found if skill not in required_skills]
    required_experience = extract_experience_years(text)
    education = extract_education(text)
    requirement_lines = [
        line for line in lines
        if re.search(r"\b(required|must|should|qualification|experience|proficient|knowledge|ability|degree|preferred|bonus)\b", line, re.I)
    ]
    # Keep a compact requirement preview for the UI; all extracted criteria remain available separately.
    return {
        "skills": required_skills,
        "preferred_skills": preferred_skills,
        "required_experience_years": required_experience,
        "education": education,
        "requirements": requirement_lines[:12],
    }
