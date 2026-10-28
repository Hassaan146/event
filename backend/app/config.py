import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "events.db")))
SOURCES_PATH = BASE_DIR / "sources.json"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
USER_AGENT = "IslamabadTechEvents/1.0 (local event discovery)"
