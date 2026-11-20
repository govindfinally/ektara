"""Deterministic post-LLM grounding and format validator."""

from __future__ import annotations

import re

from app.schemas import EvidenceItem, OpenerLLMOutput, ScrapedSite, ValidationResult

MIN_QUOTE_CHARS = 8


def normalize_text(text: str) -> str:
    """Normalize text for resilient substring matching."""
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def verify_evidence_quotes(
    evidence: list[EvidenceItem],
    scraped_text: str,
) -> tuple[int, list[str]]:
    """Verify each LLM evidence quote appears in the scraped website text."""
    norm_source = normalize_text(scraped_text)
    verified = 0
    warnings: list[str] = []

    for item in evidence:
        norm_quote = normalize_text(item.quote)
        if len(norm_quote) < MIN_QUOTE_CHARS:
            warnings.append(
                f"Evidence quote too short to verify ({len(norm_quote)} chars): {item.quote!r}"
            )
        elif norm_quote in norm_source:
            verified += 1
        else:
            warnings.append(
                f"Evidence quote not found in scraped site text: {item.quote!r}"
            )

    return verified, warnings


def validate_opener(draft: OpenerLLMOutput, scraped: ScrapedSite) -> ValidationResult:
    """Run deterministic format, quote-grounding, and founder-name checks on an LLM draft."""
    warnings: list[str] = []

    line_count_ok = len(draft.opener_lines) == 3 and all(
        bool(line.strip()) and "\n" not in line and "\r" not in line
        for line in draft.opener_lines
    )
    if not line_count_ok:
        warnings.append("Opener must contain exactly 3 non-empty single-line sentences.")

    haystack = f"{scraped.combined_text}\n{scraped.structured_metadata}"
    norm_haystack = normalize_text(haystack)

    founder_name_found = False
    hallucinated_founder = False
    if draft.founder_name and draft.founder_name.strip():
        norm_founder = normalize_text(draft.founder_name)
        if norm_founder and norm_founder in norm_haystack:
            founder_name_found = True
        else:
            hallucinated_founder = True
            warnings.append(
                f"Founder name '{draft.founder_name}' was not found on the scraped website."
            )

    quotes_verified, quote_warnings = verify_evidence_quotes(draft.evidence, haystack)
    warnings.extend(quote_warnings)

    quotes_total = len(draft.evidence)
    if quotes_total == 0:
        warnings.append("No supporting evidence quotes were returned.")

    passed = line_count_ok and not hallucinated_founder and quotes_verified >= 1
    return ValidationResult(
        passed=passed,
        line_count_ok=line_count_ok,
        quotes_verified=quotes_verified,
        quotes_total=quotes_total,
        founder_name_found=founder_name_found,
        warnings=warnings,
    )
