# Problem Statement

- **Status**: Implemented (Phases 2–4 Complete; Ready for Local Live Smoke Test & Submission)

## 1. Objective
Build a lightweight, zero-spend web tool (FastAPI + vanilla HTML/CSS/JS + BeautifulSoup4 + Google Gemini `gemini-3.5-flash-lite`) that accepts a company's website URL and produces a **3-line cold email opener** addressed to its founder, grounded strictly in verifiable content fetched from that website and positioned around the target value proposition (an AI management team for ~$10K–$50K/month software companies).

## 2. Input & Output Contract
- **Input**:
  - `url` (`string`): A company website address submitted via `POST /api/generate` or the web UI (auto-prepends `https://` when omitted).
- **Output (`200 OK` JSON)**:
  - `company_name` (`string`): Company name observed on the fetched pages.
  - `founder_name` (`string | null`): Founder/co-founder/CEO name **only if** verbatim present in scraped HTML/JSON-LD; otherwise `null`.
  - `opener_lines` (`list[str]`, exact length `3`): Three concise, single-sentence lines (Line 1: verifiable site observation; Line 2: operational bridge; Line 3: low-friction relevance + question).
  - `evidence` (`list[{claim, quote, source_url}]`): Exact supporting quotes from fetched pages and their URLs.
  - `signals` (`list[str]`): 2–4 concise factual tags observed on the site.
  - `validation` (`{passed, line_count_ok, quotes_verified, founder_name_found, warnings}`): Deterministic post-LLM audit results.
  - `trace_metrics` (`{pages_fetched, extracted_chars, scrape_ms, llm_ms, cached, model}`): Code vs. model execution metrics.
- **Error Contract (`4xx`/`5xx` JSON)**:
  - Honest, actionable error states for invalid/unsafe URLs (`400`), unreachable/timed-out sites (`502`), bot blocks (`403`/`429`), JS-only empty pages (`422`), missing `GEMINI_API_KEY` (`500`), or Gemini quota limits (`429`).

## 3. Core Boundary: Code vs. Model
- **Deterministic Code (`app/scraper.py`, `app/validator.py`, `app/main.py`, `scripts/logger.py`)**:
  - URL normalization and SSRF IP/scheme protection.
  - Bounded `httpx.AsyncClient` fetching (homepage + up to 2 high-signal same-domain pages: `/about`, `/company`, `/team`, `/founders`, `/pricing`, `/product`).
  - `BeautifulSoup4` (`html.parser`) extraction of `<title>`, meta/OG tags, JSON-LD (`Organization`/`founder`), headings, and visible body text capped at ~10,000 chars.
  - Early JS-shell / empty-body detection (`< 120` chars) before spending an LLM call.
  - 15-minute in-memory TTL cache and structured runtime logging (`logs/app.log`).
  - Post-LLM deterministic verification: exact 3-line count check, quote-in-source check, and founder-name null/no-guess check.
- **LLM / Model (`app/generator.py` + `prompts/system_prompt.txt` & `prompts/user_prompt.txt`)**:
  - Single structured Interactions API call (`client.interactions.create` on `gemini-3.5-flash-lite`, `store=False`, `thinking_level="low"`) synthesizing extracted text into `company_name`, `founder_name`, 3-line `opener_lines`, `evidence`, and `signals`.

## 4. Functional & Non-Functional Requirements
- **Checkable facts only**: Zero hallucinated metrics, features, or founder names.
- **Zero-dollar spend ($0)**: Free/open Python libraries (`fastapi`, `httpx`, `beautifulsoup4`, `google-genai`) and Google AI Studio free tier for development/demo.
- **Scoped simplicity (~2 hours)**: Single FastAPI process serving both API and static vanilla HTML/CSS/JS UI—no Node/React build chain.
- **Externalized prompts**: System and user prompts stored in `prompts/system_prompt.txt` and `prompts/user_prompt.txt` for clean iteration and interview walkthrough clarity.
- **Observability & Scale Math**: Structured runtime logs plus verified cost/failure analysis at **1,000 runs/day**.

## 5. Out of Scope
- Sending cold emails or contacting any founder/company.
- Paid scraping proxies, headless Playwright clusters (documented as future scale upgrade), or paid enrichment APIs.
- Bypassing logins, paywalls, or anti-bot CAPTCHAs.
- Guessing or fabricating unverified founder identities, revenue numbers, or product claims.

## 6. Remaining Confirmations Before Build (Phase 2)
1. Confirm `GEMINI_API_KEY` availability in `.env` for live testing.
2. Confirm public sharing target: public GitHub repo (run locally with `uvicorn`), free hosted web demo, or both (with confidential `docs/TASK_BRIEF.md` excluded).
