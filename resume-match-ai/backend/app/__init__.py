"""AI Resume Matching API."""
from pathlib import Path
from dotenv import load_dotenv

# Load backend/.env for local runs; existing process environment variables take precedence.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
