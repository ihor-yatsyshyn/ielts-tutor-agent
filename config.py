"""Центральна конфігурація. Нічого не хардкодимо, все з env."""
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/ielts_tutor.db")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
AGENT_MAX_TOOL_ROUNDS = int(os.getenv("AGENT_MAX_TOOL_ROUNDS", "4"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

PROMPT_VERSION = "tutor-2026-11-v1"
WRITING_RUBRIC_VERSION = "writing-2026-11"
SPEAKING_RUBRIC_VERSION = "speaking-text-2026-11"

# стартові ваги пріоритету (spec 8.4), не наукова формула, підлягає калібруванню
PRIORITY_WEIGHTS = {
    "weakness": 0.30, "target_relevance": 0.20, "recency": 0.15,
    "repeated_error": 0.15, "confidence": 0.10, "preference": 0.05, "variety": 0.05,
}
