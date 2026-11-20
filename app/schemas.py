"""Pydantic schemas for scraping, LLM structured output, validation, and API responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Incoming request payload from the UI or API caller."""

    url: str = Field(..., min_length=1, description="Company website URL to analyze.")


class ScrapedPage(BaseModel):
    """Extracted content and metadata from a single fetched HTML page."""

    url: str
    final_url: str
    status_code: int
    title: str = ""
    meta_description: str = ""
    headings: list[str] = Field(default_factory=list)
    text: str = ""
    json_ld: list[dict[str, Any]] = Field(default_factory=list)


class ScrapedSite(BaseModel):
    """Aggregated multi-page site payload passed to the LLM and validator."""

    input_url: str
    normalized_url: str
    pages: list[ScrapedPage]
    structured_metadata: str
    combined_text: str
    extracted_chars: int
    scrape_ms: int


class EvidenceItem(BaseModel):
    """Single claim backed by a verbatim quote and source URL from scraped content."""

    claim: str = Field(..., description="Short factual claim referenced in the opener.")
    quote: str = Field(..., description="Verbatim quote copied from the scraped text.")
    source_url: str = Field(..., description="Fetched page URL containing the quote.")


class OpenerLLMOutput(BaseModel):
    """Structured JSON schema enforced on Gemini Flash-Lite responses."""

    company_name: str = Field(..., description="Company name observed on the website.")
    founder_name: str | None = Field(
        default=None,
        description="Founder/co-founder/CEO name only if explicitly present on the site.",
    )
    opener_lines: list[str] = Field(
        ...,
        description="Exactly 3 concise single-sentence cold email opener lines.",
    )
    evidence: list[EvidenceItem] = Field(
        default_factory=list,
        description="Verbatim evidence items supporting claims in the opener.",
    )
    signals: list[str] = Field(
        default_factory=list,
        description="2-4 concise factual tags observed on the website.",
    )


class ValidationResult(BaseModel):
    """Deterministic post-LLM grounding and format verification report."""

    passed: bool
    line_count_ok: bool
    quotes_verified: int
    quotes_total: int
    founder_name_found: bool
    warnings: list[str] = Field(default_factory=list)


class TraceMetrics(BaseModel):
    """Execution breakdown separating deterministic scraping from LLM latency."""

    pages_fetched: list[str]
    extracted_chars: int
    scrape_ms: int
    llm_ms: int
    cached: bool = False
    model: str


class GenerateResponse(BaseModel):
    """Final API response returned to the browser UI."""

    company_name: str
    founder_name: str | None = None
    opener_lines: list[str]
    evidence: list[EvidenceItem]
    signals: list[str]
    validation: ValidationResult
    trace_metrics: TraceMetrics
