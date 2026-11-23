# Technical Approach — TalentScope Resume Matcher

## Design overview

The system is split into a dependency-free HTML/CSS/JavaScript presentation layer served by FastAPI, focused parsing/matching modules, and SQLAlchemy persistence. The separation makes the scoring logic independently testable and keeps upload/API concerns out of the matching algorithm.

## Request flow

1. Recruiter pastes or uploads a JD.
2. `parser.parse_job_description()` extracts canonical required skills, preferred skills, explicit years of experience and qualification level.
3. Recruiter uploads multiple PDF/DOCX files in one multipart request.
4. `parser.extract_document_text()` reads each file; `parse_resume()` extracts candidate fields and a normalized skill list.
5. `matcher.score_candidate()` calculates the score and evidence for each candidate.
6. FastAPI stores extracted text, structured fields, score components and explanation in SQLite by default (or another configured SQLAlchemy database).
7. JavaScript renders candidates sorted by score and fetches a detail record when a row is opened.

FastAPI returns the frontend page at `/` and serves its static files under `/static`. The frontend calls the API on the same origin.

## Score calculation

### Skill sub-score

Required skills are treated as the primary skill evidence. A line labeled `Preferred`, `Nice-to-have`, `Good-to-have`, `Bonus` or `Desirable` is parsed as preferred criteria.

When both lists exist:

```text
required_coverage  = matched_required / total_required
preferred_coverage = matched_preferred / total_preferred
skill_score = 100 × (0.85 × required_coverage + 0.15 × preferred_coverage)
```

If there are no preferred skills, the skill score is simply required coverage × 100. If the JD only contains preferred skills, their coverage is used.

### Other components

```text
semantic_score  = cosine_similarity(JD_embedding, resume_embedding) × 100
experience_score = min(candidate_years / required_years, 1) × 100
education_score = 100 if detected education meets/exceeds requirement,
                  proportional partial credit if lower, otherwise 0
```

Experience and education components are omitted when the JD has no explicit requirement for them. The final score normalizes the base weights over components that are active:

```text
overall_score = Σ(component_score × component_base_weight)
                / Σ(active_component_base_weights)

Base component weights:
  Skills              0.50
  Content similarity  0.25
  Experience          0.15
  Education           0.10
```

Candidate name, email and phone are extracted for display only and are not part of the score.

## Semantic model and fallback

The intended production/demo path uses `sentence-transformers/all-MiniLM-L6-v2` to encode the JD and each resume. The JD embedding is cached across candidates in the current process. Cosine similarity is clamped to `[0, 1]` and converted to a percentage.

If the embedding library/model cannot be loaded, the matcher switches to scikit-learn TF-IDF bigram cosine similarity. That fallback is lexical, not semantic. `similarity_engine` is returned in API responses so a recruiter can see which method was used. For a technical demonstration focused on semantic matching, run at least one analysis with the Sentence Transformers model loaded and mention the fallback separately.

## Parsing strategy

- PDF: pypdf extracts selectable text from each page.
- DOCX: python-docx extracts paragraphs and table cells.
- Skills: canonical dictionary plus aliases, using token boundaries to avoid common substring false positives.
- Experience: explicit `N years of experience` patterns take precedence; employment-year ranges are a fallback.
- Education: a simple degree-level taxonomy (Diploma, Bachelor's, Master's, PhD).
- Contact: regular expressions for email and phone.

This is intentionally deterministic and inspectable. It is not a universal resume parser; the skills taxonomy and regex patterns should be expanded against a representative, consented resume set.

## API surface

- `POST /api/jobs`: create a job from JD text or PDF/DOCX.
- `POST /api/jobs/{job_id}/resumes`: batch process up to 50 resumes.
- `GET /api/jobs/{job_id}/results`: ranking summaries.
- `GET /api/jobs/{job_id}/candidates/{candidate_id}`: candidate detail and score explanation.
- `DELETE /api/jobs/{job_id}`: remove a job and associated candidate records.

## Testing and demonstration

The backend tests cover alias matching, experience parsing, preferred-vs-required JD parsing and candidate analysis. The included end-to-end smoke test can be reproduced by pasting `sample_resumes/job_description.txt` into the UI and uploading all ten sample resumes; the sample set mixes PDF and DOCX formats.

## Known trade-offs

- Scanned/image-only PDFs are not OCR-processed.
- Resume layout/column order may reduce parsing quality.
- The finite skills dictionary can miss synonyms or domain-specific skills.
- Year-range experience inference is approximate; explicit years statements are preferred.
- A single whole-document embedding can hide section-level differences. Section-based comparisons or a cross-encoder reranker are future improvements.
- The prototype has no authentication, authorization or audit workflow. Use synthetic data only until privacy, security, retention and fairness controls are implemented.
