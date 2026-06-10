"""
Centralized configuration for the HR Multi-Agent System.
Loads environment variables and provides typed settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """Application settings loaded from environment variables."""

    # LLM Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{PROJECT_ROOT / 'hr_system.db'}"
    )

    # API Server
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # Agent Configuration
    RESUME_SHORTLIST_THRESHOLD: int = int(os.getenv("RESUME_SHORTLIST_THRESHOLD", "60"))
    MAX_INTERVIEWS_PER_CANDIDATE: int = int(os.getenv("MAX_INTERVIEWS_PER_CANDIDATE", "3"))

    @classmethod
    def validate(cls) -> None:
        """Validate that required settings are present."""
        if not cls.OPENAI_API_KEY or cls.OPENAI_API_KEY == "sk-your-key-here":
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Please copy .env.example to .env and add your API key."
            )


settings = Settings()
