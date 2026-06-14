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
    """Application settings loaded from environment variables.

    Values are resolved at instantiation time so that env changes
    between import and first use are respected.
    """

    def __init__(self) -> None:
        # LLM Configuration
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
        self.LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.LLM_TEMPERATURE: float = self._parse_float("LLM_TEMPERATURE", 0.1)

        # Database
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            f"sqlite:///{PROJECT_ROOT / 'hr_system.db'}",
        )

        # API Server
        self.API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
        self.API_PORT: int = self._parse_int("API_PORT", 8000)

        # Agent Configuration
        self.RESUME_SHORTLIST_THRESHOLD: int = self._parse_int(
            "RESUME_SHORTLIST_THRESHOLD", 60
        )
        self.MAX_INTERVIEWS_PER_CANDIDATE: int = self._parse_int(
            "MAX_INTERVIEWS_PER_CANDIDATE", 3
        )

        # Agent Guardrails
        self.AGENT_RECURSION_LIMIT: int = self._parse_int(
            "AGENT_RECURSION_LIMIT", 25
        )
        self.AGENT_TIMEOUT_SECONDS: int = self._parse_int(
            "AGENT_TIMEOUT_SECONDS", 120
        )
        self.AGENT_MAX_RETRIES: int = self._parse_int(
            "AGENT_MAX_RETRIES", 2
        )

    # --- helpers ---------------------------------------------------------

    @staticmethod
    def _parse_float(key: str, default: float) -> float:
        raw = os.getenv(key)
        if raw is None:
            return default
        try:
            return float(raw)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _parse_int(key: str, default: int) -> int:
        raw = os.getenv(key)
        if raw is None:
            return default
        try:
            return int(raw)
        except (ValueError, TypeError):
            return default

    # --- validation ------------------------------------------------------

    def validate(self) -> None:
        """Validate that required settings are present."""
        if not self.OPENAI_API_KEY or self.OPENAI_API_KEY == "sk-your-key-here":
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Please copy .env.example to .env and add your API key."
            )


settings = Settings()
