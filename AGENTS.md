# AGENTS.md — AI Handoff & Workspace Guide

## Project Snapshot
- **What we are building**: A small zero-spend tool that takes a company's website URL and drafts a grounded 3-line cold email opener to its founder based strictly on what the site says (built for a stealth AI product serving ~$10K–$50K/month software companies).
- **Current Status**: Phases 0–5 complete (full FastAPI + HTML/CSS/JS + BeautifulSoup4 + Gemini 3.5 Flash-Lite app, validator, tests, `.env`, `.gitignore` confidentiality guard, and word-counted submission package in `docs/SUBMISSION_DRAFT.md` ready for form submission).

## Cold-Start Read Order
Any AI model or developer opening `d:\EKatra` cold should read these files in order without needing prior chat history:

1. `AGENTS.md` (this file — entry point, update rules, guardrails)
2. `docs/CONTEXT.md` (live project state, local environment, file index, open decisions, immediate next step)
3. `docs/TASK_BRIEF.md` (confidential prompt brief, rules, hard word limits, submission fields)
4. `docs/PROBLEM_STATEMENT.md` (problem definition, scope, acceptance criteria)
5. `docs/PLAN.md` (phased roadmap and technical architecture)
6. `docs/DECISIONS.md` (architecture and tooling decisions, `DEC-NNN`)
7. `docs/WORK_DONE.md` (chronological record of completed deliverables)
8. `logs/AI_LOGS.md` (recent AI actions; or run `python scripts/logger.py tail`)
9. `prompts/system_prompt.txt` & `prompts/user_prompt.txt` (LLM system instructions and runtime prompt template)

## Mandatory Update Protocol (Every Turn / Every Meaningful Step)
Keep the workspace self-contained so any subsequent model can resume seamlessly:

1. **State changes**: Update `docs/CONTEXT.md` whenever the phase, status, key files, or open questions change.
2. **Scope & plan changes**: Update `docs/PROBLEM_STATEMENT.md` or `docs/PLAN.md` whenever requirements, boundaries, or architecture evolve.
3. **Design choices**: Append a `DEC-NNN` entry to `docs/DECISIONS.md` for every architectural, provider, or tooling decision.
4. **Log AI activity**: Run:
   ```bash
   python scripts/logger.py ai --actor "<model-or-agent>" --category <cat> --phase "<phase>" --summary "..." --files ...
   ```
   This atomically updates `logs/ai_events.jsonl`, `logs/AI_LOGS.md`, and `logs/app.log`.
5. **Log completed deliverables**: Run:
   ```bash
   python scripts/logger.py work --phase "<phase>" --title "..." --summary "..." --files ... --verification "..."
   ```
   This updates `docs/WORK_DONE.md` (summary table + detailed entry) and logs a matching `work_done` AI event.
6. **Runtime logs**: Application modules should use `from scripts.logger import get_logger` so runtime events write to `logs/app.log`, or CLI scripts can call `python scripts/logger.py log`.
7. **Check hard word limits**: Before finalizing submission copy in `docs/SUBMISSION_DRAFT.md`, run:
   ```bash
   python scripts/logger.py wordcount --file docs/SUBMISSION_DRAFT.md --section RUN --limit 50
   python scripts/logger.py wordcount --file docs/SUBMISSION_DRAFT.md --section ANALYSIS --limit 150
   ```

## Hard Rules & Confidentiality Guardrails
1. **Confidentiality**: The task brief explicitly asks to keep the product concept and this test private. Never push `docs/TASK_BRIEF.md` or confidential prompt wording to a public repository; sanitize or exclude internal docs before sharing a public demo/repo link.
2. **Real, checkable facts only**: Never fabricate company details, founder names, metrics, or citations. Every claim in a generated opener must trace directly to fetched website content.
3. **Hard word limits**:
   - `How to run it`: max **50 words**.
   - `What runs in code, what runs in the model, and what breaks at 1,000 runs a day, cost included`: max **150 words**.
4. **Do not contact anyone**: Never send emails, submit forms, or contact anyone on any prospect list.
5. **Zero-dollar constraint**: Use free/open tools and free tiers; document exact cost behavior at 1,000 runs/day.
6. **Interview walkthrough readiness**: Keep code, decisions, and logs clean, readable, and easy to explain end-to-end.
