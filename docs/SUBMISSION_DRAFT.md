# Submission Draft (Final Ready-to-Paste Package)

All hard word limits have been verified with `python scripts/logger.py wordcount`.

## 1. Demo or Repo Link
- **Repository URL**: `https://github.com/govindfinally/ektara`
- **Public Sharing Checklist**:
  - [x] `.env` and `docs/TASK_BRIEF.md` are excluded in `.gitignore` so API keys and confidential test instructions are never pushed publicly
  - [ ] Push branch/main to GitHub and verify `https://github.com/govindfinally/ektara` opens in an incognito window ("anyone with the link can view")

## 2. How to run it (`40 / 50 words` — Hard Limit: 50)
Validate with:
```bash
python scripts/logger.py wordcount --file docs/SUBMISSION_DRAFT.md --section RUN --limit 50
```

<!-- RUN_START -->
Clone the repo, activate Python 3.11 venv, install requirements.txt, and copy .env.example to .env with your GEMINI_API_KEY. Start the server via uvicorn app.main:app --reload and open http://127.0.0.1:8000. Enter any company URL and click Draft Opener. Run pytest -v for tests.
<!-- RUN_END -->

## 3. What runs in code, what runs in the model, and what breaks at 1,000 runs a day, cost included (`128 / 150 words` — Hard Limit: 150)
Validate with:
```bash
python scripts/logger.py wordcount --file docs/SUBMISSION_DRAFT.md --section ANALYSIS --limit 150
```

<!-- ANALYSIS_START -->
Code handles deterministic work: URL normalization, SSRF IP blocking, async httpx fetching (homepage plus 2 high-signal pages), BeautifulSoup4 HTML extraction (capped at 10,000 chars), JS-shell/bot-block rejection, 15-minute caching, and post-LLM checks enforcing 3 lines, verbatim quote matching, and zero invented founder names. The model (gemini-3.5-flash-lite via Google GenAI Interactions API) only synthesizes cleaned site text into structured JSON (opener, evidence quotes, signals). At 1,000 runs/day: (1) Gemini free tier breaks first (~500 RPD/15 RPM limit), requiring Paid Tier 1 at ~$1.78/day (~$53/month) for ~3k input and ~350 output tokens per run ($1.28/day on gemini-3.1-flash-lite); (2) JS-only SPAs fail static extraction without adding Playwright (~$15/month RAM overhead); (3) single-IP scraping hits 403/429 bot challenges without per-domain throttling; (4) sites omitting founders require generic greetings unless paired with external enrichment.
<!-- ANALYSIS_END -->
