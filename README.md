# TalentScope — AI-Based Resume Matching & Candidate Ranking

A full-stack prototype that compares a Job Description (JD) with a batch of candidate resumes, ranks candidates, and explains the evidence behind each score.

> **Important:** This is a recruiter decision-support prototype, not an automated hiring decision system. Review original resumes and validate extracted information before making decisions. The included resumes contain fictional names and reserved `.test` email addresses only.

## Features implemented

- Paste a JD or upload it as PDF/DOCX.
- Upload multiple resumes in one batch (up to 50; PDF and DOCX; 10 MB per file).
- Extract readable text from PDFs and DOCX files, including DOCX table text.
- Extract candidate name, email, phone, years of experience, education level and skills.
- Detect a small, editable canonical skill dictionary with aliases (e.g. `SpringBoot` → `Spring Boot`, `Postgres` → `PostgreSQL`).
- Semantic JD/resume similarity with Sentence Transformers (`all-MiniLM-L6-v2`) when available.
- TF-IDF cosine similarity fallback when the embedding model is unavailable or disabled.
- Weighted 0–100 fit score, matched/missing skills, experience/education fit, reasons and component-level score explanation.
- Candidate ranking table with sorting/search and a candidate detail view.
- SQLite persistence by default; SQLAlchemy can be configured for PostgreSQL.
- Ten synthetic sample resumes (a mix of PDF and DOCX) and automated parser/matcher tests.

## Architecture

```text
HTML/CSS/JavaScript frontend served by FastAPI (localhost:8000)
        |
        | same-origin HTTP / JSON + multipart uploads
        v
FastAPI backend
  |-- parser.py       PDF/DOCX extraction + field/skill extraction
  |-- matcher.py      embeddings / TF-IDF + transparent scoring
  |-- models.py       Job and Candidate SQLAlchemy models
  |-- database.py     SQLite by default (PostgreSQL URL supported)
        |
        v
     SQLite DB
```

### Stack

- **Frontend:** HTML, CSS and vanilla JavaScript; no frontend framework or package manager required.
- **Backend:** Python, FastAPI, SQLAlchemy.
- **Document parsing:** pypdf and python-docx.
- **NLP/matching:** Sentence Transformers + cosine similarity; scikit-learn TF-IDF fallback.
- **Persistence:** SQLite by default; `DATABASE_URL` can select another SQLAlchemy-supported database.

## Matching algorithm

The application scores evidence extracted from the JD and resume. It does not use candidate name, email or phone number in the matching score.

### 1. Extract JD criteria

The JD parser identifies:

- Required skills from a canonical skill dictionary and aliases.
- Required years of experience when an explicit years statement is present.
- A qualification level when a degree is explicitly mentioned.
- Requirement-like lines for inspection in the API response.

### 2. Extract candidate evidence

For each resume, the parser extracts contact fields, explicit experience (or a conservative employment-year-range fallback), education level, skills and resume text. OCR is not included: image-only/scanned PDFs are rejected with a useful error and must be converted to text or OCR-processed before upload.

### 3. Calculate component scores

| Component | Base weight | Calculation |
|---|---:|---|
| Skill coverage | 50% | Required-skill coverage; when preferred skills exist, the skill sub-score is 85% required coverage + 15% preferred coverage |
| Content similarity | 25% | Cosine similarity between JD and resume embeddings, scaled to 0–100 |
| Experience fit | 15% | `min(candidate years / required years, 1) × 100` |
| Education fit | 10% | 100 when detected level meets/exceeds JD level; proportional partial credit for a lower detected level; 0 when not detected |

Only applicable components are included. For example, if the JD has no explicit experience requirement, experience is omitted from the score. The active weights are normalized by their sum:

```text
overall_score = sum(component_score × base_weight) / sum(active_base_weights)
```

This means a JD with no explicit degree or experience requirement is not penalized for those missing criteria. The UI displays the active components and the backend returns the component scores and engine used.

### 4. Semantic similarity

The preferred engine is `sentence-transformers/all-MiniLM-L6-v2`. It creates sentence/document embeddings for the JD and resume, then calculates cosine similarity. This captures related wording better than exact keyword matching alone.

If Sentence Transformers cannot be imported or its model cannot be loaded/downloaded, the service falls back to TF-IDF bigram cosine similarity so the prototype remains runnable. **TF-IDF is lexical similarity, not semantic understanding.** The API response and dashboard show which engine was used. For the strongest assignment demonstration, install the Sentence Transformers dependency and allow the model to be downloaded before the demo.

Preferred skills are detected from lines marked `preferred`, `nice-to-have`, `good-to-have`, `bonus` or `desirable`; they contribute a smaller share (15%) of the skill sub-score when present. The skill list is intentionally a transparent, editable dictionary rather than a hidden LLM extraction step. Add role-specific skills/aliases in `backend/app/parser.py` as needed. This is one of the first areas to extend for production-grade coverage.

## Quick start (local development)

Python 3.11 or 3.12 is recommended. No Node.js installation is needed.

### Run the application

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env  # Windows: copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000> for the frontend. The API docs are available at <http://localhost:8000/docs> and the health endpoint at <http://localhost:8000/api/health>.

The first scoring request may download the Sentence Transformers model. For an offline/lightweight demo, set `USE_SENTENCE_TRANSFORMERS=false` in the environment before starting the API. This uses TF-IDF fallback instead.

### Try the sample data

1. Open `sample_resumes/job_description.txt` and paste its content into the JD field.
2. Select all ten files inside `sample_resumes/` (`.pdf` and `.docx`).
3. Click **Analyze & rank candidates**.
4. Sort/search the table and click a candidate to inspect matched/missing skills, score components, extracted contact/education/experience and resume text preview.

All sample identities and contact details are synthetic. Do not add real candidate PII to a public demo repository.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Health and configured similarity engine |
| `POST` | `/api/jobs` | Create job from multipart JD text or uploaded PDF/DOCX |
| `POST` | `/api/jobs/{job_id}/resumes` | Upload and analyze a batch of resumes |
| `GET` | `/api/jobs/{job_id}/results` | Get ranked candidate summaries |
| `GET` | `/api/jobs/{job_id}/candidates/{candidate_id}` | Get full candidate-level analysis |
| `DELETE` | `/api/jobs/{job_id}` | Delete a job and associated candidates |

FastAPI's Swagger UI (`/docs`) can be used to exercise every endpoint without the frontend.

## Run tests

From the `backend` folder:

```bash
pip install -r requirements.txt
pytest -q
```

The matcher tests force the local TF-IDF path for deterministic, network-free execution.

## Configuration

Backend environment variables (see `backend/.env.example`):

- `USE_SENTENCE_TRANSFORMERS=true|false`
- `EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2`
- `DATABASE_URL=sqlite:///...` or a PostgreSQL SQLAlchemy connection URL.

For PostgreSQL, install a driver such as `pip install 'psycopg[binary]'` and set `DATABASE_URL`, for example:

```text
postgresql+psycopg://user:password@localhost:5432/resume_match
```

FastAPI serves the frontend at `/` and its CSS/JavaScript from `/static`. The frontend uses the same origin for API requests; no separate static server or CORS configuration is needed.

## Project structure

```text
resume-match-ai/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── parser.py
│   │   ├── matcher.py
│   │   ├── models.py
│   │   └── database.py
│   ├── tests/test_matching.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── sample_resumes/
│   ├── job_description.txt
│   ├── generate_samples.py
│   └── ten synthetic PDF/DOCX resumes
└── README.md
```

## Known limitations and sensible next improvements

1. **Parsing:** Resume layouts vary. Current parsing is text-first and rule-based; scanned PDFs need OCR, and complex columns/tables can affect reading order.
2. **Skill taxonomy:** The dictionary is intentionally finite. Add aliases, domain skills and skill categories for each hiring domain; consider spaCy or a reviewed LLM extraction step for broader coverage.
3. **Experience:** Explicit statements are preferred. Date-range inference is approximate and does not fully interpret overlapping roles, internships, part-time work or career breaks.
4. **Semantic relevance:** A single document embedding can miss section-level context. A stronger version could split resumes/JDs into sections, compare skills/experience/project evidence separately, and optionally rerank with a cross-encoder.
5. **Fairness and privacy:** Do not score protected attributes or infer them from names/photos. Add retention controls, access controls, audit logs, encryption and bias testing before any real-world use. A human recruiter must verify extracted facts and make the decision.
6. **Evaluation:** Build a labeled test set and track parsing precision/recall, ranking quality (e.g. NDCG@k) and score calibration across job families.

## Demo walkthrough (3–5 minutes)

1. Explain the architecture and why the parser, matcher and API are separate modules.
2. Paste the sample JD and upload all 10 synthetic resumes (show batch handling and mixed PDF/DOCX support).
3. Explain the score formula and identify active weights for this JD.
4. Show the ranking table and open both a strong and a weaker candidate.
5. Point out matched/missing skills, experience/education evidence, reasons and similarity engine.
6. Open `/docs`, run a health check and describe how the database and API endpoints work.


