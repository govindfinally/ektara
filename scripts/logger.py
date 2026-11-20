"""Zero-dependency logging, AI activity tracking, work-done updates, and word-count CLI."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT_DIR / "logs"
DOCS_DIR = ROOT_DIR / "docs"

AI_EVENTS_FILE = LOGS_DIR / "ai_events.jsonl"
AI_LOGS_MD = LOGS_DIR / "AI_LOGS.md"
APP_LOG_FILE = LOGS_DIR / "app.log"
WORK_DONE_MD = DOCS_DIR / "WORK_DONE.md"

WORK_TABLE_MARKER = "<!-- WORK_DONE_TABLE_END -->"
WORK_DETAILS_MARKER = "<!-- WORK_DONE_DETAILS_END -->"

AI_CATEGORIES = (
    "init",
    "plan",
    "decision",
    "action",
    "code",
    "test",
    "doc_update",
    "work_done",
    "error",
    "handoff",
)
AI_STATUSES = ("done", "in_progress", "blocked", "info")

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def now_iso() -> str:
    """Return local timezone-aware ISO-8601 timestamp with second precision."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


class _LFFileHandler(logging.FileHandler):
    """FileHandler that enforces LF line endings across platforms."""

    def _open(self):  # type: ignore[override]
        return open(self.baseFilename, self.mode, encoding=self.encoding, newline="\n")


def get_logger(name: str = "ekatra", level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger writing to logs/app.log (UTF-8, LF) and stdout."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter(_LOG_FORMAT)

        file_handler = _LFFileHandler(APP_LOG_FILE, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger


def _ensure_ai_logs_md() -> None:
    """Create logs/AI_LOGS.md with its header if missing or empty."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if not AI_LOGS_MD.exists() or not AI_LOGS_MD.read_text(encoding="utf-8").strip():
        header = (
            "# AI Activity Logs\n\n"
            "Chronological human-readable log of AI actions, synchronized with "
            "`logs/ai_events.jsonl` and `logs/app.log` via `scripts/logger.py`.\n\n"
        )
        AI_LOGS_MD.write_text(header, encoding="utf-8", newline="\n")


def _ensure_work_done_md() -> None:
    """Create docs/WORK_DONE.md with required markers if missing."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    if not WORK_DONE_MD.exists() or not WORK_DONE_MD.read_text(encoding="utf-8").strip():
        template = (
            "# Work Done Log\n\n"
            "Chronological record of completed deliverables. Add new entries with:\n"
            "```bash\n"
            'python scripts/logger.py work --phase "<phase>" --title "..." --summary "..." --files ... --verification "..."\n'
            "```\n\n"
            "## Summary Table\n\n"
            "| ID | Timestamp | Phase | Title | Files | Verified |\n"
            "|---|---|---|---|---|---|\n"
            f"{WORK_TABLE_MARKER}\n\n"
            "## Detailed Work Entries\n\n"
            f"{WORK_DETAILS_MARKER}\n"
        )
        WORK_DONE_MD.write_text(template, encoding="utf-8", newline="\n")


def next_ai_id() -> str:
    """Return the next sequential AI-NNNN identifier based on logs/ai_events.jsonl."""
    max_num = 0
    if AI_EVENTS_FILE.exists():
        for raw_line in AI_EVENTS_FILE.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                match = re.fullmatch(r"AI-(\d+)", str(record.get("id", "")))
                if match:
                    max_num = max(max_num, int(match.group(1)))
            except json.JSONDecodeError:
                match = re.search(r"AI-(\d+)", line)
                if match:
                    max_num = max(max_num, int(match.group(1)))
    return f"AI-{max_num + 1:04d}"


def next_work_id() -> str:
    """Return the next sequential WD-NNN identifier based on docs/WORK_DONE.md."""
    max_num = 0
    if WORK_DONE_MD.exists():
        content = WORK_DONE_MD.read_text(encoding="utf-8")
        for match in re.finditer(r"\bWD-(\d+)\b", content):
            max_num = max(max_num, int(match.group(1)))
    return f"WD-{max_num + 1:03d}"


def _escape_md_cell(value: str) -> str:
    """Sanitize text for safe insertion into a Markdown table cell."""
    return value.replace("|", "\\|").replace("\r\n", " ").replace("\n", " ").strip()


def log_ai_event(
    summary: str,
    actor: str = "ai-agent",
    category: str = "action",
    phase: str = "Phase 0",
    details: str = "",
    files: list[str] | None = None,
    status: str = "done",
) -> dict[str, Any]:
    """Append a structured AI activity event to JSONL, Markdown, and app.log."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_ai_logs_md()

    clean_files = [f for f in (files or []) if f]
    event: dict[str, Any] = {
        "id": next_ai_id(),
        "timestamp": now_iso(),
        "actor": actor,
        "category": category,
        "phase": phase,
        "summary": summary,
        "details": details,
        "files": clean_files,
        "status": status,
    }

    with AI_EVENTS_FILE.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")

    files_md = ", ".join(f"`{f}`" for f in clean_files) if clean_files else "none"
    md_lines = [
        f"### [{event['id']}] {event['timestamp']} | {phase} | `{category}` (`{status}`)",
        f"- **Actor**: {actor}",
        f"- **Summary**: {summary}",
        f"- **Files**: {files_md}",
    ]
    if details.strip():
        md_lines.append(f"- **Details**: {details.strip()}")
    md_block = "\n".join(md_lines) + "\n\n"

    with AI_LOGS_MD.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(md_block)

    get_logger("ai_log").info(
        "[%s] [%s] (%s/%s) %s: %s",
        event["id"],
        phase,
        category,
        status,
        actor,
        summary,
    )
    return event


def log_work_done(
    title: str,
    summary: str,
    phase: str = "Phase 0",
    files: list[str] | None = None,
    verification: str = "Verified",
    actor: str = "ai-agent",
) -> dict[str, Any]:
    """Record completed work in docs/WORK_DONE.md and log a synchronized AI event."""
    _ensure_work_done_md()
    content = WORK_DONE_MD.read_text(encoding="utf-8")
    if WORK_TABLE_MARKER not in content or WORK_DETAILS_MARKER not in content:
        raise RuntimeError(
            f"{WORK_DONE_MD} is missing required markers "
            f"{WORK_TABLE_MARKER!r} or {WORK_DETAILS_MARKER!r}."
        )

    work_id = next_work_id()
    ts = now_iso()
    clean_files = [f for f in (files or []) if f]
    files_cell = ", ".join(f"`{f}`" for f in clean_files) if clean_files else "none"

    table_row = (
        f"| {work_id} | {_escape_md_cell(ts)} | {_escape_md_cell(phase)} | "
        f"{_escape_md_cell(title)} | {_escape_md_cell(files_cell)} | "
        f"{_escape_md_cell(verification)} |"
    )
    detail_lines = [
        f"### [{work_id}] {title}",
        f"- **Timestamp**: {ts}",
        f"- **Phase**: {phase}",
        f"- **Summary**: {summary}",
        f"- **Files**: {files_cell}",
        f"- **Verification**: {verification}",
    ]
    detail_block = "\n".join(detail_lines) + "\n\n"

    updated = content.replace(WORK_TABLE_MARKER, f"{table_row}\n{WORK_TABLE_MARKER}", 1)
    updated = updated.replace(
        WORK_DETAILS_MARKER, f"{detail_block}{WORK_DETAILS_MARKER}", 1
    )
    WORK_DONE_MD.write_text(updated, encoding="utf-8", newline="\n")

    log_ai_event(
        summary=f"Completed {work_id}: {title}",
        actor=actor,
        category="work_done",
        phase=phase,
        details=f"{summary} (Verification: {verification})",
        files=clean_files,
        status="done",
    )

    return {
        "id": work_id,
        "timestamp": ts,
        "title": title,
        "phase": phase,
        "files": clean_files,
        "verification": verification,
    }


def count_words(text: str) -> int:
    """Count whitespace-delimited words strictly to match form limit counters."""
    return len(re.findall(r"\S+", text))


def _extract_section(text: str, section: str) -> str:
    """Extract content between <!-- <SECTION>_START --> and <!-- <SECTION>_END -->."""
    start_tag = f"<!-- {section}_START -->"
    end_tag = f"<!-- {section}_END -->"
    pattern = re.compile(
        re.escape(start_tag) + r"(.*?)" + re.escape(end_tag),
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise ValueError(
            f"Section markers {start_tag!r} ... {end_tag!r} not found in input."
        )
    return match.group(1).strip()


def _tail_lines(path: Path, count: int) -> list[str]:
    """Return the last `count` non-empty lines from `path`."""
    if not path.exists():
        return []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return lines[-count:] if count > 0 else []


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="EKatra project logging, AI audit, work-done, and word-count CLI."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ai_p = sub.add_parser("ai", help="Log an AI action event.")
    ai_p.add_argument("--summary", required=True, help="Concise action summary.")
    ai_p.add_argument("--actor", default="ai-agent", help="Model or agent name.")
    ai_p.add_argument("--category", default="action", choices=AI_CATEGORIES)
    ai_p.add_argument("--phase", default="Phase 0", help="Project phase label.")
    ai_p.add_argument("--details", default="", help="Extended details.")
    ai_p.add_argument("--files", nargs="*", default=[], help="Related file paths.")
    ai_p.add_argument("--status", default="done", choices=AI_STATUSES)

    work_p = sub.add_parser("work", help="Log completed deliverable to docs/WORK_DONE.md.")
    work_p.add_argument("--title", required=True, help="Deliverable title.")
    work_p.add_argument("--summary", required=True, help="Summary of completed work.")
    work_p.add_argument("--phase", default="Phase 0", help="Project phase label.")
    work_p.add_argument("--files", nargs="*", default=[], help="Files created/modified.")
    work_p.add_argument("--verification", default="Verified", help="Verification note.")
    work_p.add_argument("--actor", default="ai-agent", help="Actor recorded in AI logs.")

    log_p = sub.add_parser("log", help="Write a standard application log line.")
    log_p.add_argument("--message", required=True, help="Log message.")
    log_p.add_argument(
        "--level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging level.",
    )
    log_p.add_argument("--component", default="ekatra", help="Logger component name.")

    tail_p = sub.add_parser("tail", help="Show recent AI events and runtime logs.")
    tail_p.add_argument("--lines", type=int, default=10, help="Lines to display.")

    wc_p = sub.add_parser("wordcount", help="Count words and check hard limits.")
    src_group = wc_p.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--text", help="Literal text string to count.")
    src_group.add_argument("--file", help="Path to text/markdown file to count.")
    wc_p.add_argument(
        "--section",
        help="Optional marker name (extracts <!-- <NAME>_START --> .. <!-- <NAME>_END -->).",
    )
    wc_p.add_argument("--limit", type=int, help="Hard maximum word limit.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "ai":
        event = log_ai_event(
            summary=args.summary,
            actor=args.actor,
            category=args.category,
            phase=args.phase,
            details=args.details,
            files=args.files,
            status=args.status,
        )
        print(f"Logged {event['id']}")
        return 0

    if args.command == "work":
        work = log_work_done(
            title=args.title,
            summary=args.summary,
            phase=args.phase,
            files=args.files,
            verification=args.verification,
            actor=args.actor,
        )
        print(f"Recorded {work['id']}: {work['title']}")
        return 0

    if args.command == "log":
        level_num = getattr(logging, args.level)
        logger = get_logger(args.component, level=level_num)
        logger.log(level_num, args.message)
        return 0

    if args.command == "tail":
        print("=== logs/ai_events.jsonl ===")
        events = _tail_lines(AI_EVENTS_FILE, args.lines)
        if not events:
            print("(empty)")
        for raw in events:
            try:
                rec = json.loads(raw)
                print(
                    f"[{rec.get('id')}] {rec.get('timestamp')} | {rec.get('phase')} | "
                    f"{rec.get('category')} ({rec.get('status')}) | {rec.get('actor')}: "
                    f"{rec.get('summary')}"
                )
            except json.JSONDecodeError:
                print(raw)

        print("\n=== logs/app.log ===")
        app_lines = _tail_lines(APP_LOG_FILE, args.lines)
        if not app_lines:
            print("(empty)")
        for line in app_lines:
            print(line)
        return 0

    if args.command == "wordcount":
        if args.text is not None:
            content = args.text
        else:
            file_path = Path(args.file)
            if not file_path.is_absolute():
                file_path = ROOT_DIR / file_path
            content = file_path.read_text(encoding="utf-8")

        if args.section:
            content = _extract_section(content, args.section)

        total = count_words(content)
        if args.limit is None:
            print(f"{total} words")
            return 0

        status = "PASS" if total <= args.limit else "FAIL"
        print(f"{total} / {args.limit} words ({status})")
        return 0 if total <= args.limit else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
