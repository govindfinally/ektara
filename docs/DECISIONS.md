# Architecture & Tooling Decisions

Record significant architectural, product, and tooling decisions chronologically as `DEC-NNN` entries.

## Entry Template
```markdown
## DEC-NNN: <Title>
- **Date**: YYYY-MM-DD
- **Status**: Accepted | Proposed | Superseded
- **Context**: Why this decision was needed.
- **Decision**: What we chose.
- **Alternatives Considered**: Other options and why they were rejected.
- **Consequences**: Trade-offs, constraints, and follow-up actions.
```

---

## DEC-001: Self-Contained Markdown + JSONL Documentation & Stdlib Python Logger Architecture
- **Date**: 2026-11-21
- **Status**: Accepted
- **Context**: Multiple AI models or fresh chat sessions need to understand the task, live context, decisions, completed work, and AI logs directly from disk without reading previous chat history, while enforcing strict submission word limits (50 and 150 words).
- **Decision**: Use `AGENTS.md` as the root cold-start entrypoint pointing to structured Markdown files in `docs/`, paired with a zero-dependency Python 3.11 standard-library CLI/module (`scripts/logger.py`) that writes synchronized machine-readable events (`logs/ai_events.jsonl`), human-readable AI logs (`logs/AI_LOGS.md`), runtime logs (`logs/app.log`), and completed work entries (`docs/WORK_DONE.md`), plus a built-in `wordcount` validator.
- **Alternatives Considered**:
  - Manually editing Markdown logs only (rejected: error-prone ID numbering, easy to drift between machine logs and docs).
  - Third-party logging/CLI packages like `click` or `rich` (rejected: requires virtual environment setup before even logging Phase 0 work).
- **Consequences**: Works out of the box on the local Python 3.11 runtime with zero installs; every future phase must keep `docs/CONTEXT.md` and `scripts/logger.py` records up to date.

---

## DEC-002: Web & Scraping Stack — FastAPI + Vanilla HTML/CSS/JS + httpx + BeautifulSoup4
- **Date**: 2026-11-21
- **Status**: Accepted (User Specified)
- **Context**: Needed a fast, simple, zero-spend stack that keeps the ~2-hour scope focused, avoids complex frontend build pipelines, and is easy to walk through in an interview.
- **Decision**: Build a single-service Python app using **FastAPI** (`uvicorn`) serving both JSON API endpoints (`POST /api/generate`, `GET /api/health`) and static **HTML/CSS/JS** (`static/`), paired with async `httpx` and `BeautifulSoup4` (`html.parser`) for bounded multi-page fetching (homepage + up to 2 high-signal pages) with SSRF IP guards and early JS-shell detection.
- **Alternatives Considered**:
  - React/Next.js + separate backend (rejected: unnecessary build tooling and CORS setup for a small single-purpose tool).
  - Playwright headless browser for all scrapes (rejected: heavy RAM/CPU footprint and slower startup on free hosting; documented as a scale upgrade for JS-only SPAs).
  - `lxml` parser dependency (rejected in favor of built-in `html.parser` to avoid C-compiler build issues across environments).
- **Consequences**: Minimal dependencies, zero CORS friction, fast startup (`< 1s`), clean unit testability; JS-only SPAs return an explicit, honest error instead of empty guesses.

---

## DEC-003: LLM API — Google Gemini Flash-Lite (`gemini-3.5-flash-lite`) via `google-genai` Interactions API
- **Date**: 2026-11-21
- **Status**: Accepted (User Specified)
- **Context**: User requested Google Flash-Lite for cost-efficient, low-latency generation within the $0 constraint while supporting clean structured outputs and accurate 1,000 runs/day unit economics.
- **Decision**: Use the official **`google-genai >= 3.2.0`** Python SDK and GA **Interactions API** (`client.interactions.create(..., store=False, thinking_level="low", response_format=...)`) targeting **`gemini-3.5-flash-lite`** by default, configurable via `GEMINI_MODEL` in `.env` (allowing drop-in switching to `gemini-3.1-flash-lite`). Avoid deprecated `google-generativeai`, `generate_content`, `gemini-2.x` models, and `temperature`/`top_p`/`top_k` params.
- **Alternatives Considered**:
  - Legacy `google-generativeai` SDK or `gemini-2.0-flash-lite` (rejected: deprecated SDK and model).
  - Larger reasoning models like `gemini-4-carbon` (rejected: higher token cost and latency than needed for grounded 3-line synthesis).
- **Consequences**: Free tier (~500 RPD / 15 RPM) covers development and demo usage at `$0`; at 1,000 runs/day (~3k input / ~350 output tokens/run), Paid Tier 1 is required at ~$1.78/day (~$53/mo) on `gemini-3.5-flash-lite` or ~$1.28/day (~$38/mo) on `gemini-3.1-flash-lite`.

---

## DEC-004: Externalized Prompt Templates (`prompts/*.txt`) & Deterministic Post-LLM Validator
- **Date**: 2026-11-21
- **Status**: Accepted
- **Context**: Keeping LLM instructions hardcoded inside Python strings reduces readability, slows prompt iteration, and makes confidentiality hygiene harder when sharing the codebase publicly.
- **Decision**: Store static grounding/formatting instructions in `prompts/system_prompt.txt` and runtime input framing in `prompts/user_prompt.txt`, injecting `OFFER_CONTEXT` from config/environment at runtime rather than hardcoding confidential brief wording in code. Enforce output invariants deterministically in `app/validator.py` (exact 3 non-empty lines, verbatim/normalized quote check against scraped text, and `founder_name` null check when absent from HTML).
- **Alternatives Considered**:
  - Single inline Python f-string inside `generator.py` (rejected: harder to inspect, diff, and walk through cleanly).
  - Relying solely on LLM instructions without post-generation verification (rejected: models can still drift on line count or invent founder names when under-constrained).
- **Consequences**: Prompts are inspectable, editable without touching Python code, and safely reusable; every model response undergoes deterministic verification before reaching the UI.

