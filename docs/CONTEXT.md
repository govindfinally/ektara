# Project Context (Live State)

- **Last Updated**: 2026-11-21
- **Current Phase**: Phases 0–5 Complete — Submission Package Verified & Ready for Git Push / Form Paste
- **Workspace Root**: `d:\EKatra`
- **Git Branch**: `feature/docs`

## Local Runtime Environment
- **OS**: Windows
- **Python**: `3.11.0` (project virtual environment at `venv/`)
- **Node.js**: `v24.14.1`
- **uv**: `0.10.10`

## Pre-Existing Workspace Notes
- `README.md` has been written with a clean, confidentiality-safe public overview and setup instructions.
- `docs/AURA.pdf` was previously deleted locally by the user (unstaged deletion in git working tree) and must not be restored.

## File Index
| Path | Purpose |
|---|---|
| `AGENTS.md` | Primary AI cold-start guide, read order, update protocol, and guardrails |
| `README.md` | Public project overview, setup steps, architecture summary, and 1,000/day cost math |
| `.env.example` | Environment template (`GEMINI_API_KEY`, `GEMINI_MODEL`, `OFFER_CONTEXT`) |
| `pytest.ini` | Pytest configuration setting `pythonpath = .` and `testpaths = tests` |
| `requirements.txt` | Frozen `venv/` dependencies (`fastapi`, `uvicorn`, `httpx`, `beautifulsoup4`, `google-genai`, `python-dotenv`, `pytest`) |
| `docs/CONTEXT.md` | Live project state, environment info, file index, and open decisions |
| `docs/TASK_BRIEF.md` | Confidential test requirements, rules, word limits, and submission fields |
| `docs/PROBLEM_STATEMENT.md` | Locked problem definition, I/O contract, and code-vs-model boundary |
| `docs/PLAN.md` | Phased roadmap, directory layout, 8-step runtime workflow, and 1,000/day cost model |
| `docs/DECISIONS.md` | Chronological Architecture Decision Records (`DEC-001`–`DEC-004`) |
| `docs/WORK_DONE.md` | Summary table and detailed entries of completed deliverables (`WD-NNN`) |
| `docs/SUBMISSION_DRAFT.md` | Staging draft for submission link, <=50-word run guide, and <=150-word analysis |
| `prompts/system_prompt.txt` | Static LLM system instructions (grounding rules, 3-line structure, founder-name rule) |
| `prompts/user_prompt.txt` | Parameterized LLM user prompt template populated at runtime with site data + offer context |
| `app/__init__.py` | Application package marker |
| `app/config.py` | Loads `.env` and provides frozen `Settings` dataclass |
| `app/schemas.py` | Pydantic models for scraping, LLM structured output, validation, and API payloads |
| `app/scraper.py` | URL normalization, SSRF IP guard, async `httpx` fetch, BeautifulSoup4 extraction |
| `app/validator.py` | Deterministic post-LLM grounding validator (3-line check, quote matching, founder guard) |
| `app/generator.py` | Loads `prompts/*.txt` and calls Gemini `gemini-3.5-flash-lite` via `google-genai` Interactions API |
| `app/main.py` | FastAPI backend (`GET /`, `GET /api/health`, `POST /api/generate`, 15-min TTL cache) |
| `static/index.html` | Single-page UI (URL input, 3-line opener card, evidence quotes, trace metrics) |
| `static/styles.css` | Editorial light theme and responsive layout styles |
| `static/app.js` | Safe DOM rendering, health status pill, copy button, and API integration |
| `tests/conftest.py` | Adds repository root to `sys.path` when running `pytest` from `tests/` |
| `tests/test_scraper.py` | Unit tests for `app/scraper.py` (runnable via `pytest` or `python tests/test_scraper.py`) |
| `tests/test_validator.py` | Unit tests for `app/validator.py` (6/6 passing via `pytest` or `python tests/test_validator.py`) |
| `tests/test_generator.py` | Unit tests for `app/generator.py` and `google-genai` SDK schema validation (5/5 passing) |
| `tests/test_api.py` | FastAPI `TestClient` suite for `/`, `/api/health`, `/api/generate`, and error paths |
| `scripts/__init__.py` | Marks `scripts/` as an importable Python package |
| `scripts/logger.py` | Zero-dependency Python stdlib logger CLI (`ai`, `work`, `log`, `tail`, `wordcount`) |
| `logs/AI_LOGS.md` | Human-readable chronological AI activity log |
| `logs/ai_events.jsonl` | Machine-readable structured AI event log (JSON Lines) |
| `logs/app.log` | Standard application and audit runtime log |

## What Is Done
- **Phase 0**: Self-contained documentation suite + zero-dependency Python logger (`WD-001`).
- **Phase 1**: Locked architecture (`FastAPI` + vanilla HTML/CSS/JS + `httpx` + `BeautifulSoup4` + `gemini-3.5-flash-lite`), externalized `prompts/*.txt`, and ADRs `DEC-002`–`DEC-004` (`WD-002`).
- **Phase 2**: Installed packages into `venv/`, built `app/config.py`, `app/schemas.py`, `app/scraper.py`, `app/validator.py` + `tests/test_validator.py` (6/6 passing) (`WD-003`, `WD-004`).
- **Phases 3–4**: Implemented `app/generator.py` + `tests/test_generator.py` (5/5 passing), `app/main.py` + `tests/test_api.py`, `static/` frontend (`node --check` passing), `README.md`, and direct `python test_*.py` execution (`WD-004`, `WD-005`).
- **Phase 5**: Configured local `.env` (`GEMINI_API_KEY` + `OFFER_CONTEXT` with placeholder fallback in `app/config.py`), added `docs/TASK_BRIEF.md` to `.gitignore` for public repo confidentiality, and verified final submission copy in `docs/SUBMISSION_DRAFT.md` (`40/50` words and `128/150` words) (`WD-006`).

## Immediate Next Step
Push the repo to GitHub (`https://github.com/govindfinally/Gleam.ai`), verify it opens in an incognito browser tab ("anyone with the link can view"), and paste the 3 fields from `docs/SUBMISSION_DRAFT.md` into the submission form.

## Pending Before Final Submission (Phase 5)
1. **Local `.env` live smoke test**: Copy `.env.example` -> `.env`, set `GEMINI_API_KEY`, run live tests against sample software company URLs.
2. **Public link & confidentiality check**: Verify public GitHub repo or hosted demo opens in incognito without exposing `docs/TASK_BRIEF.md`.
