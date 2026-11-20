"""Application configuration loaded from environment variables and defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT_DIR / "prompts"
STATIC_DIR = ROOT_DIR / "static"

load_dotenv(ROOT_DIR / ".env", override=False)

DEFAULT_OFFER_CONTEXT = (
    "An AI operations assistant for small software companies that monitors key "
    "business metrics and automates follow-up actions."
)


@dataclass(frozen=True)
class Settings:
    """Runtime settings for scraping, Gemini generation, and caching."""

    gemini_api_key: str
    gemini_model: str = "gemini-3.5-flash-lite"
    offer_context: str = DEFAULT_OFFER_CONTEXT
    http_timeout_seconds: float = 8.0
    max_redirects: int = 5
    max_response_bytes: int = 1_500_000
    max_extra_pages: int = 2
    max_total_chars: int = 10_000
    min_usable_chars: int = 120
    cache_ttl_seconds: int = 900
    user_agent: str = "Mozilla/5.0 (compatible; FounderOpenerBot/1.0)"


_PLACEHOLDER_OFFER = "Describe your B2B product value proposition here."


def get_settings() -> Settings:
    """Build Settings from the current environment."""
    raw_offer = os.getenv("OFFER_CONTEXT", "").strip()
    if not raw_offer or raw_offer == _PLACEHOLDER_OFFER:
        offer_context = DEFAULT_OFFER_CONTEXT
    else:
        offer_context = raw_offer

    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
        or "gemini-3.5-flash-lite",
        offer_context=offer_context,
    )
