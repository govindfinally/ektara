# Project Plan

- **Status**: Phases 0–5 Complete (Ready for Final Git Push & Form Submission)

## Phased Roadmap

| Phase | Scope | Status |
|---|---|---|
| **Phase 0** | Documentation suite, AI handoff protocol (`AGENTS.md`), zero-dependency logger (`scripts/logger.py`), and initial logs | `[x]` Done |
| **Phase 1** | Finalize Problem Statement, FastAPI + BeautifulSoup4 + Gemini 3.5 Flash-Lite architecture, externalized prompts (`prompts/*.txt`), and 1,000/day cost/failure model | `[x]` Done |
| **Phase 2** | Implement deterministic URL fetching, HTML cleaning, page/signal extraction, and validator (`app/scraper.py`, `app/validator.py`) + unit tests | `[x]` Done |
| **Phase 3** | Implement Gemini 3.5 Flash-Lite generator (`app/generator.py`), prompt loading, and FastAPI backend (`app/main.py`) + API tests | `[x]` Done |
| **Phase 4** | Build vanilla HTML/CSS/JS frontend (`static/`), add public `README.md`, and run automated unit/syntax checks | `[x]` Done |
| **Phase 5** | Configure `.env`, guard confidential `docs/TASK_BRIEF.md` in `.gitignore`, finalize & word-count-verify `docs/SUBMISSION_DRAFT.md` (40/50w and 128/150w) | `[x]` Done |

## Phase Checklists

### Phase 0: Handoff Docs & Logging Infrastructure
- [x] Create `AGENTS.md` and `.gitignore`
- [x] Create `docs/` documentation suite (`CONTEXT.md`, `TASK_BRIEF.md`, `PROBLEM_STATEMENT.md`, `PLAN.md`, `DECISIONS.md`, `WORK_DONE.md`, `SUBMISSION_DRAFT.md`)
- [x] Implement `scripts/logger.py` with `ai`, `work`, `log`, `tail`, and `wordcount` commands
- [x] Verify CLI, Python module imports, and log outputs end-to-end

### Phase 1: Problem Statement & Technical Plan
- [x] Lock stack: FastAPI + vanilla HTML/CSS/JS + httpx + BeautifulSoup4 (`DEC-002`)
- [x] Lock LLM API: Google Gemini `gemini-3.5-flash-lite` via `google-genai >= 3.2.0` Interactions API (`DEC-003`)
- [x] Externalize prompts to `prompts/system_prompt.txt` and `prompts/user_prompt.txt` (`DEC-004`)
- [x] Define scraping scope (homepage + up to 2 high-signal pages, timeouts, SSRF guards, JS-shell early fail)
- [x] Lock deterministic grounding checks (3-line enforcement, verbatim quote verification, founder-name null guard)
- [x] Model 1,000 runs/day bottlenecks and $0 vs. paid cost math

### Phase 2: Environment & Deterministic Core
- [x] Use existing `venv/`, install dependencies, freeze `requirements.txt`, and add `.env.example`
- [x] Add `pytest.ini` + `tests/conftest.py` so `pytest` resolves `app` and `scripts` from root or `tests/`
- [x] Implement `app/config.py`, `app/schemas.py`, `app/scraper.py` + `tests/test_scraper.py` (5/5 sync tests verified in sandbox; 3 async `MockTransport` tests ready for local terminal)
- [x] Implement `app/validator.py` (`normalize_text`, `verify_evidence_quotes`, `validate_opener`) + `tests/test_validator.py` (6/6 passing)

### Phase 3–5
- [x] Phase 3: Implement `app/generator.py` (loading `prompts/*.txt` + `client.interactions.create`) and `app/main.py` (`GET /`, `GET /api/health`, `POST /api/generate`), plus `tests/test_generator.py` (5/5 passing) and `tests/test_api.py`.
- [x] Phase 4: Build `static/index.html`, `static/styles.css`, `static/app.js`, and confidentiality-safe `README.md`; verify `node --check static/app.js` and FastAPI route registrations.
- [x] Phase 5: Configured `.env` (`GEMINI_API_KEY` + `OFFER_CONTEXT`), guarded `docs/TASK_BRIEF.md` in `.gitignore`, and verified `docs/SUBMISSION_DRAFT.md` word limits (`40 / 50` and `128 / 150` words).

## Planned Project Directory Layout

```text
d:\EKatra\
├── prompts/
│   ├── system_prompt.txt  # Static grounding rules, 3-line structure, and schema rules
│   └── user_prompt.txt    # Runtime prompt template populated with offer context + scraped site data
├── app/
│   ├── __init__.py
│   ├── config.py          # Env settings (GEMINI_API_KEY, GEMINI_MODEL=gemini-3.5-flash-lite, OFFER_CONTEXT, limits)
│   ├── schemas.py         # Pydantic models for API request/response and LLM structured JSON schema
│   ├── scraper.py         # URL normalization, SSRF guard, async httpx fetch, BeautifulSoup4 extraction
│   ├── generator.py       # Loads prompts/*.txt and calls Gemini Interactions API (gemini-3.5-flash-lite)
│   ├── validator.py       # Deterministic 3-line check, verbatim quote check, founder-name guard
│   └── main.py            # FastAPI app: GET /, GET /api/health, POST /api/generate + 15-min TTL cache
├── static/
│   ├── index.html         # Single-page UI (URL input, 3-line opener card, evidence & trace view)
│   ├── styles.css         # Minimal responsive styling
│   └── app.js             # Fetch /api/generate, copy button, error states, expandable evidence panel
├── tests/
│   ├── test_scraper.py    # URL/SSRF, BeautifulSoup extraction, JSON-LD founder parsing, JS-shell detection
│   ├── test_validator.py  # Strict 3-line check, quote matching, unverified founder-name handling
│   └── test_api.py        # FastAPI endpoint tests (mocked fetch + mocked Gemini response)
├── scripts/
│   └── logger.py          # Shared logging, AI audit, work-done, and wordcount CLI/module
├── docs/                  # Internal docs & decisions (kept out of public demo/repo shares)
├── logs/                  # Runtime + AI logs
├── requirements.txt       # fastapi, uvicorn[standard], httpx, beautifulsoup4, google-genai>=3.2.0, python-dotenv, pytest
└── .env.example           # Template for GEMINI_API_KEY, GEMINI_MODEL, and OFFER_CONTEXT
```

## End-to-End Runtime Workflow

1. **User Input (`static/index.html` → `static/app.js`)**: User enters a company website URL and clicks **Draft Opener**; `app.js` sends `POST /api/generate` with `{"url": "..."}`.
2. **Cache Check (`app/main.py`)**: FastAPI validates the request payload and checks a 15-minute in-memory TTL cache to avoid redundant scrapes and LLM calls on repeat runs.
3. **SSRF Guard & Homepage Fetch (`app/scraper.py`)**: Normalizes missing `https://`, restricts schemes to `http`/`https`, resolves DNS and rejects private/loopback/link-local IPs, then fetches the homepage via `httpx.AsyncClient` (`8s` timeout, max `5` redirects, max `1.5 MB` response body) and parses HTML using `BeautifulSoup4` (`html.parser`).
4. **Targeted Crawl & Extraction (`app/scraper.py`)**: Selects up to 2 high-signal same-domain links (`/about`, `/company`, `/team`, `/founders`, `/pricing`, `/product`), fetches them concurrently, and extracts `<title>`, meta/OG tags, JSON-LD (`Organization`/`founder`), `<h1>`/`<h2>` headings, and cleaned visible text (stripping `<script>`, `<style>`, `<svg>`, `<noscript>`, `<iframe>`) capped at **~10,000 chars (~2,500 tokens)**. Fails fast with a clear error if total cleaned text is `< 120` chars (empty JS SPA shell or bot block).
5. **Prompt Assembly & Gemini Call (`app/generator.py`)**: Reads `prompts/system_prompt.txt` and `prompts/user_prompt.txt`, injects `OFFER_CONTEXT` plus fetched metadata/text, and makes a single structured call to **`gemini-3.5-flash-lite`** via `google-genai >= 3.2.0` `client.interactions.create(..., store=False, thinking_level="low", response_format=...)` (without deprecated `temperature`/`top_p`/`top_k` params).
6. **Deterministic Verification (`app/validator.py`)**: Enforces `len(opener_lines) == 3` with non-empty lines, verifies cited `evidence` quotes appear in the scraped text (normalized matching), enforces the founder-name grounding guard (`founder_name_found`), and flags/rejects unverified metrics.
7. **Observability (`scripts/logger.py`)**: Logs request latency breakdown (scrape ms vs. model ms), fetched URLs, validation status, and error reasons via `get_logger()` to `logs/app.log`.
8. **UI Response (`app/main.py` → `static/app.js`)**: Returns structured JSON (`opener_lines`, `evidence`, `signals`, `validation`, `trace_metrics`) to the browser, rendering the 3-line opener card, copy button, clickable source quotes, and code-vs-model timing trace.

## 1,000 Runs/Day Failure & Cost Model

- **Free Tier Ceiling**: Google AI Studio free tier for Flash-Lite caps around ~500 RPD / ~15 RPM per project, so 1,000 runs/day exceeds the free tier and requires Paid Tier 1.
- **Paid LLM Unit Economics (1,000 runs/day at ~3,000 input tokens + ~350 output tokens per run = 3.0M input + 0.35M output tokens/day)**:
  - **`gemini-3.5-flash-lite`** (`$0.30 / 1M` input, `$2.50 / 1M` output): `$0.90 + $0.88` ≈ **`$1.78/day` (~`$53/month`)**.
  - **`gemini-3.1-flash-lite`** (`$0.25 / 1M` input, `$1.50 / 1M` output, drop-in via `GEMINI_MODEL`): `$0.75 + $0.53` ≈ **`$1.28/day` (~`$38/month`)**.
- **Operational Failure Modes at 1,000 Runs/Day**:
  1. **JS-Rendered SPAs (~20–30% of SaaS sites)**: `httpx + BeautifulSoup4` receives an empty root shell (`< 120` chars); requires an optional Playwright fallback (+`$10–$30/mo` RAM/CPU hosting and 3–5× latency).
  2. **WAF / Bot Challenges (`403`/`429`)**: A single server IP hitting 1,000 domains/day triggers Cloudflare/rate-limit challenges; needs per-domain throttling, caching, and optional proxy rotation only if scraping protected sites.
  3. **Missing Founder Names**: Many SaaS sites do not list founder names in public HTML; our deterministic guard refuses to guess and falls back cleanly (`founder_name: null`) unless paired with external enrichment.
  4. **Slow Origin Timeouts & Worker Contention**: Unresponsive target sites can tie up request workers; requires strict timeouts, bounded concurrency semaphores, and persistent caching (SQLite/Redis).
