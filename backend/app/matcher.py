"""Transparent weighted scoring with Sentence-Transformers and a TF-IDF fallback."""
from __future__ import annotations
import os
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
USE_SENTENCE_TRANSFORMERS = os.getenv("USE_SENTENCE_TRANSFORMERS", "true").lower() in {"1", "true", "yes"}


class SemanticSimilarity:
    def __init__(self) -> None:
        self._model = None
        self._attempted = False
        self.mode = "tfidf-fallback"
        self.load_error: str | None = None
        self._jd_embedding_cache: dict[str, np.ndarray] = {}

    def _load(self) -> None:
        if self._attempted:
            return
        self._attempted = True
        if not USE_SENTENCE_TRANSFORMERS:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(MODEL_NAME)
            self.mode = "sentence-transformers"
        except Exception as exc:  # prototype remains usable without a model download
            self.load_error = str(exc)
            self._model = None
            self.mode = "tfidf-fallback"

    def compare(self, jd_text: str, resume_text: str) -> float:
        self._load()
        if self._model is not None:
            # Cache the JD vector across candidates in the same analysis batch.
            jd_vector = self._jd_embedding_cache.get(jd_text)
            if jd_vector is None:
                jd_vector = self._model.encode([jd_text], normalize_embeddings=True)[0]
                if len(self._jd_embedding_cache) >= 8:
                    self._jd_embedding_cache.pop(next(iter(self._jd_embedding_cache)))
                self._jd_embedding_cache[jd_text] = jd_vector
            resume_vector = self._model.encode([resume_text], normalize_embeddings=True)[0]
            similarity = float(np.dot(jd_vector, resume_vector))
            return round(max(0.0, min(1.0, similarity)) * 100, 1)
        # Fallback is lexical rather than truly semantic. It keeps local demos working.
        try:
            matrix = TfidfVectorizer(ngram_range=(1, 2), stop_words="english").fit_transform(
                [jd_text, resume_text]
            )
            score = float(cosine_similarity(matrix[0:1], matrix[1:2])[0, 0])
            return round(max(0.0, min(1.0, score)) * 100, 1)
        except ValueError:
            return 0.0


similarity_engine = SemanticSimilarity()


def _education_score(candidate: dict[str, Any], required: dict[str, Any]) -> float:
    required_rank = int((required or {}).get("rank", 0))
    actual_rank = int((candidate or {}).get("rank", 0))
    if required_rank <= 0:
        return 100.0
    if actual_rank <= 0:
        return 0.0
    if actual_rank >= required_rank:
        return 100.0
    return round(actual_rank / required_rank * 100, 1)


def score_candidate(jd_text: str, jd_requirements: dict[str, Any], resume_text: str, extracted: dict[str, Any]) -> dict[str, Any]:
    required_skills = jd_requirements.get("skills", [])
    preferred_skills = jd_requirements.get("preferred_skills", [])
    candidate_skills = extracted.get("skills", [])
    matched_required = [skill for skill in required_skills if skill in candidate_skills]
    missing = [skill for skill in required_skills if skill not in candidate_skills]
    matched_preferred = [skill for skill in preferred_skills if skill in candidate_skills]
    missing_preferred = [skill for skill in preferred_skills if skill not in candidate_skills]
    matched = matched_required + matched_preferred
    if required_skills and preferred_skills:
        required_coverage = len(matched_required) / len(required_skills)
        preferred_coverage = len(matched_preferred) / len(preferred_skills)
        skill_score = round((0.85 * required_coverage + 0.15 * preferred_coverage) * 100, 1)
    elif required_skills:
        skill_score = round((len(matched_required) / len(required_skills)) * 100, 1)
    elif preferred_skills:
        skill_score = round((len(matched_preferred) / len(preferred_skills)) * 100, 1)
    else:
        skill_score = None

    semantic_score = similarity_engine.compare(jd_text, resume_text)
    required_years = jd_requirements.get("required_experience_years")
    actual_years = extracted.get("experience_years")
    if required_years and required_years > 0:
        experience_score = 0.0 if actual_years is None else round(min(actual_years / required_years, 1.0) * 100, 1)
    else:
        experience_score = None

    required_education = jd_requirements.get("education", {})
    education_required = int((required_education or {}).get("rank", 0)) > 0
    education_score = _education_score(extracted.get("education", {}), required_education) if education_required else None

    # Only criteria that actually exist in the JD are included in the denominator.
    components: list[tuple[str, float, float]] = []
    if skill_score is not None:
        components.append(("skills", skill_score, 0.50))
    components.append(("semantic_similarity", semantic_score, 0.25))
    if experience_score is not None:
        components.append(("experience", experience_score, 0.15))
    if education_score is not None:
        components.append(("education", education_score, 0.10))
    active_weight = sum(weight for _, _, weight in components)
    overall = round(sum(score * weight for _, score, weight in components) / active_weight, 1) if active_weight else 0.0

    reasons = []
    if required_skills:
        reasons.append(f"Matched {len(matched_required)} of {len(required_skills)} required skills.")
    if preferred_skills:
        reasons.append(f"Matched {len(matched_preferred)} of {len(preferred_skills)} preferred skills (15% of the skills sub-score).")
    reasons.append(f"Resume/JD content similarity is {semantic_score:.1f}/100 using {similarity_engine.mode}.")
    if experience_score is not None:
        if actual_years is None:
            reasons.append(f"The JD asks for {required_years:g} years; experience could not be confidently extracted.")
        else:
            reasons.append(f"Detected {actual_years:g} years against {required_years:g} required years.")
    if education_score is not None:
        actual_level = (extracted.get("education") or {}).get("level") or "not detected"
        required_level = (required_education or {}).get("level") or "the stated qualification"
        reasons.append(f"Education detected: {actual_level}; JD qualification: {required_level}.")
    if missing:
        reasons.append("Missing required skills: " + ", ".join(missing) + ".")
    if missing_preferred:
        reasons.append("Preferred skills not detected: " + ", ".join(missing_preferred) + ".")
    if not required_skills and not preferred_skills:
        reasons.append("No skills from the built-in skill dictionary were detected in the JD; score relies more heavily on content similarity and any explicit qualifications.")

    score_components = {
        "skills": skill_score,
        "semantic_similarity": semantic_score,
        "experience": experience_score,
        "education": education_score,
        "weights_before_normalisation": {
            name: weight for name, _, weight in components
        },
        "active_weight_total": round(active_weight, 2),
        "engine": similarity_engine.mode,
    }
    return {
        "match_score": overall,
        "matched_skills": matched,
        "missing_skills": missing,
        "matched_preferred_skills": matched_preferred,
        "missing_preferred_skills": missing_preferred,
        "score_components": score_components,
        "reasons": reasons,
    }
