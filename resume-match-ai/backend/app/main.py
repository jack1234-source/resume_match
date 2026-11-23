from __future__ import annotations
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .matcher import score_candidate, similarity_engine
from .models import Candidate, Job
from .parser import extract_document_text, parse_job_description, parse_resume


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

Base.metadata.create_all(bind=engine)
app = FastAPI(
    title="ResumeMatch AI API",
    description="Prototype API for explainable resume-to-job-description matching.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


def _candidate_summary(candidate: Candidate) -> dict:
    analysis = candidate.analysis or {}
    return {
        "id": candidate.id,
        "name": candidate.candidate_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "file_name": candidate.file_name,
        "experience_years": candidate.experience_years,
        "match_score": candidate.match_score,
        "matched_skills": analysis.get("matched_skills", []),
        "missing_skills": analysis.get("missing_skills", []),
        "matched_preferred_skills": analysis.get("matched_preferred_skills", []),
        "missing_preferred_skills": analysis.get("missing_preferred_skills", []),
        "education": (candidate.extracted or {}).get("education", {}),
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "resume-match-ai",
        "similarity_engine": similarity_engine.mode,
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    }


@app.post("/api/jobs")
async def create_job(
    title: str = Form("Untitled role"),
    jd_text: str = Form(""),
    jd_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Create a job from pasted JD text or an uploaded PDF/DOCX file."""
    content = jd_text.strip()
    if jd_file and jd_file.filename:
        raw = await jd_file.read()
        try:
            content = extract_document_text(jd_file.filename, raw)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"JD file: {exc}") from exc
    if len(content) < 30:
        raise HTTPException(status_code=400, detail="Enter a Job Description or upload a readable PDF/DOCX file (at least 30 characters).")

    requirements = parse_job_description(content)
    job = Job(title=title.strip() or "Untitled role", jd_text=content, requirements=requirements)
    db.add(job)
    db.commit()
    db.refresh(job)
    return {
        "id": job.id,
        "title": job.title,
        "requirements": job.requirements,
        "jd_preview": job.jd_text[:600],
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@app.post("/api/jobs/{job_id}/resumes")
async def upload_resumes(
    job_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Parse and rank a batch of up to 50 PDF/DOCX resumes."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if not files:
        raise HTTPException(status_code=400, detail="Select at least one resume.")
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Upload no more than 50 resumes in one batch.")

    accepted: list[dict] = []
    rejected: list[dict] = []
    for upload in files:
        filename = upload.filename or "unnamed-file"
        try:
            raw = await upload.read()
            resume_text = extract_document_text(filename, raw)
            extracted = parse_resume(resume_text, filename)
            analysis = score_candidate(job.jd_text, job.requirements or {}, resume_text, extracted)
            candidate = Candidate(
                job_id=job.id,
                file_name=filename[:255],
                candidate_name=(extracted.get("name") or "Unknown candidate")[:200],
                email=extracted.get("email"),
                phone=extracted.get("phone"),
                experience_years=extracted.get("experience_years"),
                match_score=analysis["match_score"],
                resume_text=resume_text,
                extracted=extracted,
                analysis=analysis,
            )
            db.add(candidate)
            db.flush()
            accepted.append(_candidate_summary(candidate))
        except ValueError as exc:
            rejected.append({"file_name": filename, "reason": str(exc)})
        except Exception as exc:
            rejected.append({"file_name": filename, "reason": f"Unexpected parsing/scoring error: {exc}"})
    db.commit()
    accepted.sort(key=lambda item: item["match_score"], reverse=True)
    return {
        "job_id": job.id,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "accepted": accepted,
        "rejected": rejected,
        "similarity_engine": similarity_engine.mode,
    }


@app.get("/api/jobs/{job_id}/results")
def get_results(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    candidates = db.query(Candidate).filter(Candidate.job_id == job_id).order_by(Candidate.match_score.desc()).all()
    return {
        "job": {
            "id": job.id,
            "title": job.title,
            "requirements": job.requirements,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        },
        "candidate_count": len(candidates),
        "candidates": [_candidate_summary(candidate) for candidate in candidates],
    }


@app.get("/api/jobs/{job_id}/candidates/{candidate_id}")
def get_candidate_detail(job_id: int, candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id, Candidate.job_id == job_id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found for this job.")
    return {
        **_candidate_summary(candidate),
        "extracted": candidate.extracted,
        "analysis": candidate.analysis,
        "resume_preview": candidate.resume_text[:2500],
    }


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    db.delete(job)
    db.commit()
    return {"deleted": True, "job_id": job_id}
