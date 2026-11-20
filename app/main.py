"""FastAPI application serving the cold-email opener API and vanilla frontend."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

_ROOT_DIR = Path(__file__).resolve().parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import STATIC_DIR, get_settings
from app.generator import GenerationError, generate_opener
from app.schemas import GenerateRequest, GenerateResponse, TraceMetrics
from app.scraper import ScrapeError, normalize_url, scrape_site
from app.validator import validate_opener
from scripts.logger import get_logger

logger = get_logger("ekatra.api")

app = FastAPI(title="Founder Cold Email Opener", version="1.0.0")

_CACHE: dict[str, tuple[float, GenerateResponse]] = {}


def clear_cache() -> None:
    """Clear the in-memory response TTL cache."""
    _CACHE.clear()


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(ScrapeError)
async def scrape_error_handler(_request: Request, exc: ScrapeError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message},
    )


@app.exception_handler(GenerationError)
async def generation_error_handler(_request: Request, exc: GenerationError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message},
    )


@app.get("/")
async def index() -> FileResponse:
    """Serve the single-page frontend."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, object]:
    """Report server status, active Gemini model, and API key availability."""
    settings = get_settings()
    return {
        "status": "ok",
        "model": settings.gemini_model,
        "api_key_configured": bool(settings.gemini_api_key),
    }


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(payload: GenerateRequest) -> GenerateResponse:
    """Scrape a company URL, draft a grounded 3-line opener, and validate claims."""
    settings = get_settings()
    normalized_url = normalize_url(payload.url)
    cache_key = f"{normalized_url}|{settings.gemini_model}"

    now = time.monotonic()
    cached_entry = _CACHE.get(cache_key)
    if cached_entry is not None:
        cached_at, cached_response = cached_entry
        if now - cached_at < settings.cache_ttl_seconds:
            hit = cached_response.model_copy(deep=True)
            hit.trace_metrics.cached = True
            logger.info("Cache hit for %s", normalized_url)
            return hit
        _CACHE.pop(cache_key, None)

    scraped = await scrape_site(payload.url, settings=settings)
    draft, llm_ms = await asyncio.to_thread(generate_opener, scraped, settings)
    validation = validate_opener(draft, scraped)

    response = GenerateResponse(
        company_name=draft.company_name,
        founder_name=draft.founder_name,
        opener_lines=draft.opener_lines,
        evidence=draft.evidence,
        signals=draft.signals,
        validation=validation,
        trace_metrics=TraceMetrics(
            pages_fetched=[page.final_url for page in scraped.pages],
            extracted_chars=scraped.extracted_chars,
            scrape_ms=scraped.scrape_ms,
            llm_ms=llm_ms,
            cached=False,
            model=settings.gemini_model,
        ),
    )
    _CACHE[cache_key] = (now, response.model_copy(deep=True))
    logger.info(
        "Generated opener for %s | passed=%s | quotes=%d/%d | scrape=%dms | llm=%dms",
        normalized_url,
        validation.passed,
        validation.quotes_verified,
        validation.quotes_total,
        scraped.scrape_ms,
        llm_ms,
    )
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

