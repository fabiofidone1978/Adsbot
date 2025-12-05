"""Configuration helpers for the Adsbot project."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, continue without it
    pass


@dataclass
class Config:
    """Runtime configuration for the bot."""

    bot_token: str
    database_url: str = "sqlite:///adsbot.db"
    openai_api_key: str = ""

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment variables."""

        token = os.getenv("BOT_TOKEN")
        if not token:
            raise RuntimeError("Missing BOT_TOKEN environment variable")

        db_url = os.getenv("DATABASE_URL", cls.database_url_from_path())
        openai_key = os.getenv("OPENAI_API_KEY", "")
        return cls(bot_token=token, database_url=db_url, openai_api_key=openai_key)

    @staticmethod
    def database_url_from_path() -> str:
        """Return a SQLite URL stored in the project root."""

        db_path = Path(os.getenv("ADS_DATABASE", "adsbot.db")).expanduser()
        return f"sqlite:///{db_path}"
 