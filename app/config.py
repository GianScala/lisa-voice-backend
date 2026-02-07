"""
Lisa Voice Agent — Configuration
=================================
Only two services needed: LiveKit + xAI.
xAI Realtime handles STT + LLM + TTS in one model.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
ENV_LOCAL_FILE = PROJECT_ROOT / ".env.local"


def _load_env_files() -> None:
    if load_dotenv is None:
        return
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE, override=False)
    if ENV_LOCAL_FILE.exists():
        load_dotenv(ENV_LOCAL_FILE, override=False)


_load_env_files()


class Config:
    """Application configuration from environment."""

    HOST: str = "0.0.0.0"

    @classmethod
    def refresh(cls) -> None:
        _load_env_files()
        cls.PORT = int(os.getenv("PORT", "8000"))
        cls.DEBUG = os.getenv("DEBUG", "true").lower() == "true"
        cls.LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
        cls.LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
        cls.LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
        cls.XAI_API_KEY = os.getenv("XAI_API_KEY", "")

    # Initialize on import
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "")
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "")
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "")

    XAI_API_KEY: str = os.getenv("XAI_API_KEY", "")

    @classmethod
    def is_livekit_configured(cls) -> bool:
        cls.refresh()
        return bool(cls.LIVEKIT_URL and cls.LIVEKIT_API_KEY and cls.LIVEKIT_API_SECRET)

    @classmethod
    def is_xai_configured(cls) -> bool:
        cls.refresh()
        return bool(cls.XAI_API_KEY)

    @classmethod
    def get_status(cls) -> Dict[str, bool]:
        cls.refresh()
        return {
            "livekit": bool(cls.LIVEKIT_URL and cls.LIVEKIT_API_KEY and cls.LIVEKIT_API_SECRET),
            "xai": bool(cls.XAI_API_KEY),
        }