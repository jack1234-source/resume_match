from pathlib import Path

from app.matcher import score_candidate, similarity_engine
from app.parser import (
    extract_document_text,
    extract_education,
    extract_experience_years,
    extract_skills,
    parse_job_description,
    parse_resume,
)


def test_skill_aliases_and_boundaries():
    skills = extract_skills("Built a RESTful API with Java, SpringBoot, PostgreSQL and Docker.")
    assert "Java" in skills
    assert "Spring Boot" in skills
    assert "PostgreSQL" in skills
    assert "Docker" in skills
    assert "React" not in skills


def test_experience_extraction():
    assert extract_experience_years("Software engineer with 4.5 years of experience") == 4.5
    assert extract_experience_years("Work history: 2020 - 2024") == 4.0


def test_document_type_is_detected_from_file_content_when_extension_is_missing():
    project_root = Path(__file__).resolve().parents[2]
    pdf_content = (project_root / "sample_resumes" / "sample_02_nisha.pdf").read_bytes()
    docx_content = (project_root / "sample_resumes" / "sample_01_aarav.docx").read_bytes()

    assert "Nisha" in extract_document_text("resume", pdf_content)
    assert "Aarav" in extract_document_text("resume", docx_content)


def test_candidate_analysis_has_explanations(monkeypatch):
    # Keep unit tests deterministic and avoid loading/downloading an embedding model.
    monkeypatch.setattr(similarity_engine, "_attempted", True)
    monkeypatch.setattr(similarity_engine, "_model", None)
    jd = "Java backend developer. Required: 3 years of experience. Skills: Java, Spring Boot, SQL. Bachelor's degree."
    resume = "Alex Morgan\nalex@example.test\n4 years of experience\nB.Tech Computer Science\nJava, Spring Boot, SQL, Docker"
    requirements = parse_job_description(jd)
    extracted = parse_resume(resume, "alex.docx")
    result = score_candidate(jd, requirements, resume, extracted)
    assert 0 <= result["match_score"] <= 100
    assert set(result["matched_skills"]) == {"Java", "Spring Boot", "SQL"}
    assert result["missing_skills"] == []
    assert result["score_components"]["skills"] == 100.0
    assert result["reasons"]


def test_jd_parser_separates_required_and_preferred():
    jd = """Backend developer.\nRequired: 4+ years of professional backend development experience.\nSkills: Java, Spring Boot, SQL.\nPreferred: Docker, AWS, Kubernetes."""
    parsed = parse_job_description(jd)
    assert parsed["required_experience_years"] == 4.0
    assert set(parsed["skills"]) == {"Java", "Spring Boot", "SQL"}
    assert set(parsed["preferred_skills"]) == {"Docker", "AWS", "Kubernetes"}


def test_contact_parser_does_not_mistake_year_ranges_for_phone_numbers():
    from app.parser import extract_contact
    contact = extract_contact("Alex Doe\nalex@example.test\nEmployment: 2020 - 2024")
    assert contact["email"] == "alex@example.test"
    assert contact["phone"] is None
    contact = extract_contact("Alex Doe\n+1 202 555 0101\nalex@example.test")
    assert contact["phone"] == "+1 202 555 0101"


def test_education_avoids_substring_false_positives():
    # 'Tomcat' contains 'mca', 'subscript' contains 'bsc', 'to be.' contains 'b.e.'
    false_positive_text = "Skills: Apache Tomcat, Docker, subscript syntax, to be. A senior engineer."
    result = extract_education(false_positive_text)
    assert result["level"] is None
    assert result["rank"] == 0

    # Genuine degrees should still match
    assert extract_education("Completed MCA from State University")["level"] == "Master's"
    assert extract_education("B.Tech in Computer Science")["level"] == "Bachelor's"
    assert extract_education("Graduated with a B.E. in 2021")["level"] == "Bachelor's"
    assert extract_education("Graduated with a B.E in 2021")["level"] == "Bachelor's"
    assert extract_education("Holds a Ph.D. in AI")["level"] == "PhD"
    assert extract_education("Holds a PhD in Computer Science")["level"] == "PhD"
    assert extract_education("Master's degree in Software Engineering")["level"] == "Master's"
    assert extract_education("Diploma in Mechanical Engineering")["level"] == "Diploma"
