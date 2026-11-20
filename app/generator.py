"""Google Gemini Flash-Lite opener generator using externalized prompt templates."""

from __future__ import annotations

import re
import time
from typing import Any

from google import genai
from pydantic import ValidationError

from app.config import PROMPTS_DIR, Settings, get_settings
from app.schemas import OpenerLLMOutput, ScrapedSite
from scripts.logger import get_logger

logger = get_logger("ekatra.generator")


class GenerationError(Exception):
    """Typed LLM generation error carrying an HTTP status code and machine error code."""

    def __init__(self, message: str, status_code: int, error_code: str) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


def load_prompt_template(filename: str) -> str:
    """Load a UTF-8 prompt template from the prompts/ directory."""
    path = PROMPTS_DIR / filename
    return path.read_text(encoding="utf-8")


def build_user_prompt(scraped: ScrapedSite, offer_context: str) -> str:
    """Populate prompts/user_prompt.txt safely using literal placeholder replacement."""
    template = load_prompt_template("user_prompt.txt")
    page_urls = "\n".join(f"- {page.final_url}" for page in scraped.pages)

    replacements = {
        "{offer_context}": offer_context,
        "{target_url}": scraped.normalized_url,
        "{page_count}": str(len(scraped.pages)),
        "{page_urls}": page_urls,
        "{structured_metadata}": scraped.structured_metadata,
        "{scraped_content}": scraped.combined_text,
    }
    prompt = template
    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, value)
    return prompt


def build_interaction_payload(scraped: ScrapedSite, settings: Settings) -> dict[str, Any]:
    """Construct the Interactions API request dictionary for Gemini Flash-Lite."""
    return {
        "model": settings.gemini_model,
        "system_instruction": load_prompt_template("system_prompt.txt"),
        "input": build_user_prompt(scraped, settings.offer_context),
        "store": False,
        "generation_config": {
            "thinking_level": "low",
            "max_output_tokens": 1024,
        },
        "response_format": [
            {
                "type": "text",
                "mime_type": "application/json",
                "schema": OpenerLLMOutput.model_json_schema(),
            }
        ],
    }


def _strip_json_fences(raw_text: str) -> str:
    text = raw_text.strip()
    fence_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.I)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def _extract_output_text(interaction: Any) -> str:
    """Extract final model text from Interactions API response or fallback steps."""
    output_text = getattr(interaction, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return _strip_json_fences(output_text)

    parts: list[str] = []
    for step in getattr(interaction, "steps", None) or []:
        if getattr(step, "type", None) != "model_output":
            continue
        for item in getattr(step, "content", None) or []:
            text = getattr(item, "text", None)
            if isinstance(text, str) and text.strip():
                parts.append(text)
    return _strip_json_fences("\n".join(parts))


def _map_sdk_error(exc: Exception) -> GenerationError:
    status = getattr(exc, "status_code", None)
    detail = str(exc)
    upper = detail.upper()

    if status == 429 or "429" in detail or "RESOURCE_EXHAUSTED" in upper or "QUOTA" in upper:
        return GenerationError(
            "Gemini API rate limit or daily free-tier quota exceeded. Please wait and retry.",
            429,
            "rate_limited",
        )
    if (
        status in (401, 403)
        or "API_KEY_INVALID" in upper
        or "UNAUTHENTICATED" in upper
        or "401" in detail
        or "403" in detail
    ):
        return GenerationError(
            "Invalid or unauthorized GEMINI_API_KEY.",
            401,
            "invalid_api_key",
        )
    return GenerationError(
        f"Gemini API request failed: {detail}",
        502,
        "llm_error",
    )


def generate_opener(
    scraped: ScrapedSite,
    settings: Settings | None = None,
    client: Any | None = None,
) -> tuple[OpenerLLMOutput, int]:
    """Generate a grounded 3-line cold email opener via Gemini Flash-Lite."""
    cfg = settings or get_settings()
    if client is None and not cfg.gemini_api_key:
        raise GenerationError(
            "GEMINI_API_KEY is not configured. Copy .env.example to .env and add your Google AI Studio API key.",
            500,
            "missing_api_key",
        )

    sdk_client = client if client is not None else genai.Client(api_key=cfg.gemini_api_key)
    payload = build_interaction_payload(scraped, cfg)

    start = time.perf_counter()
    try:
        interaction = sdk_client.interactions.create(**payload)
    except GenerationError:
        raise
    except Exception as exc:
        logger.warning("Gemini API call failed for %s: %s", scraped.normalized_url, exc)
        raise _map_sdk_error(exc) from exc
    llm_ms = int((time.perf_counter() - start) * 1000)

    raw_text = _extract_output_text(interaction)
    if not raw_text:
        raise GenerationError(
            "Gemini returned an empty response.",
            502,
            "invalid_llm_output",
        )

    try:
        draft = OpenerLLMOutput.model_validate_json(raw_text)
    except ValidationError as exc:
        logger.warning("Failed to parse LLM JSON output for %s: %s", scraped.normalized_url, exc)
        raise GenerationError(
            "Gemini output did not match the expected JSON schema.",
            502,
            "invalid_llm_output",
        ) from exc

    logger.info(
        "Generated %d lines for %s with %s in %d ms",
        len(draft.opener_lines),
        scraped.normalized_url,
        cfg.gemini_model,
        llm_ms,
    )
    return draft, llm_ms
