"""Deterministic, SSRF-safe async HTTP fetcher and BeautifulSoup4 HTML extractor."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import re
import socket
import time
import urllib.parse
from collections.abc import Callable
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.config import Settings, get_settings
from app.schemas import ScrapedPage, ScrapedSite
from scripts.logger import get_logger

logger = get_logger("ekatra.scraper")

_PRIORITY_TOKENS: dict[str, int] = {
    "about": 100,
    "company": 95,
    "team": 95,
    "founders": 95,
    "founder": 95,
    "story": 85,
    "pricing": 80,
    "product": 75,
    "features": 70,
}

_SKIP_EXTENSIONS = (
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".css",
    ".js",
    ".zip",
    ".xml",
    ".json",
    ".woff",
    ".woff2",
)

_SKIP_SEGMENTS = {
    "login",
    "signin",
    "signup",
    "register",
    "auth",
    "privacy",
    "terms",
    "legal",
    "cookies",
    "cookie",
    "careers",
    "jobs",
    "status",
    "support",
    "help",
    "docs",
}

_NOISE_TAGS = ("script", "style", "noscript", "svg", "iframe", "template", "canvas")


class ScrapeError(Exception):
    """Typed scraping error carrying an HTTP status code and machine error code."""

    def __init__(self, message: str, status_code: int, error_code: str) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host.split("%", 1)[0])
        return True
    except ValueError:
        return False


def _is_restricted_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def normalize_url(raw_url: str) -> str:
    """Validate and normalize an incoming website URL to http/https without fragments."""
    cleaned = (raw_url or "").strip()
    if not cleaned:
        raise ScrapeError("Please enter a website URL.", 400, "invalid_url")

    if "://" not in cleaned:
        cleaned = f"https://{cleaned}"

    parsed = urllib.parse.urlsplit(cleaned)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ScrapeError(
            "Only http:// and https:// website URLs are supported.",
            400,
            "invalid_url",
        )

    hostname = (parsed.hostname or "").lower().rstrip(".")
    if (
        not hostname
        or hostname == "localhost"
        or hostname.endswith(".local")
        or hostname.endswith(".internal")
        or ("." not in hostname and not _is_ip_literal(hostname))
    ):
        raise ScrapeError(
            "Please provide a valid public website domain.",
            400,
            "invalid_url",
        )

    normalized = parsed._replace(scheme=scheme, fragment="")
    return urllib.parse.urlunsplit(normalized)


def assert_public_host(
    hostname: str,
    resolver: Callable[..., Any] = socket.getaddrinfo,
) -> None:
    """Block loopback, private, link-local, multicast, and reserved IP targets (SSRF guard)."""
    clean_host = (hostname or "").strip().lower().rstrip(".")
    if not clean_host:
        raise ScrapeError("Missing hostname in URL.", 400, "invalid_url")

    if _is_ip_literal(clean_host):
        ip = ipaddress.ip_address(clean_host.split("%", 1)[0])
        if _is_restricted_ip(ip):
            raise ScrapeError(
                "Private or local network addresses are not allowed.",
                400,
                "invalid_url",
            )
        return

    try:
        addr_info = resolver(clean_host, None)
    except (socket.gaierror, OSError) as exc:
        raise ScrapeError(
            f"Could not resolve website host '{clean_host}'.",
            502,
            "unreachable",
        ) from exc

    if not addr_info:
        raise ScrapeError(
            f"Could not resolve website host '{clean_host}'.",
            502,
            "unreachable",
        )

    for entry in addr_info:
        sockaddr = entry[4]
        ip_raw = str(sockaddr[0]).split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(ip_raw)
        except ValueError:
            continue
        if _is_restricted_ip(ip):
            raise ScrapeError(
                "Target website resolves to a private or restricted IP address.",
                400,
                "invalid_url",
            )


def _strip_www(hostname: str) -> str:
    host = (hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def _looks_like_bot_challenge(html: str) -> bool:
    sample = html[:8000].lower()
    if "just a moment" in sample and (
        "cf-browser-verification" in sample or "cloudflare" in sample
    ):
        return True
    return "attention required! | cloudflare" in sample


def _extract_json_ld(soup: BeautifulSoup) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for tag in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        raw = tag.string if tag.string is not None else tag.get_text()
        if not raw or not raw.strip():
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
        elif isinstance(parsed, list):
            records.extend(item for item in parsed if isinstance(item, dict))
    return records


def extract_page(html: str, url: str, final_url: str, status_code: int) -> ScrapedPage:
    """Extract metadata, JSON-LD, headings, and clean visible text with BeautifulSoup4."""
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    if soup.title and soup.title.string:
        title = re.sub(r"\s+", " ", soup.title.string).strip()
    if not title:
        og_title = soup.find("meta", attrs={"property": re.compile(r"^og:title$", re.I)})
        if og_title and og_title.get("content"):
            title = re.sub(r"\s+", " ", str(og_title["content"])).strip()

    meta_description = ""
    for attr_key, attr_val in (("name", "description"), ("property", "og:description")):
        meta_tag = soup.find("meta", attrs={attr_key: re.compile(f"^{attr_val}$", re.I)})
        if meta_tag and meta_tag.get("content"):
            meta_description = re.sub(r"\s+", " ", str(meta_tag["content"])).strip()
            break

    json_ld = _extract_json_ld(soup)

    for noise in soup.find_all(_NOISE_TAGS):
        noise.decompose()

    headings: list[str] = []
    seen_headings: set[str] = set()
    for heading_tag in soup.find_all(["h1", "h2"]):
        text = re.sub(r"\s+", " ", heading_tag.get_text(" ", strip=True)).strip()
        if text and text not in seen_headings:
            seen_headings.add(text)
            headings.append(text)

    body_root = soup.body or soup
    raw_lines = body_root.get_text(separator="\n").splitlines()
    clean_lines: list[str] = []
    prev_line = ""
    for raw_line in raw_lines:
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line and line != prev_line:
            clean_lines.append(line)
            prev_line = line

    return ScrapedPage(
        url=url,
        final_url=final_url,
        status_code=status_code,
        title=title,
        meta_description=meta_description,
        headings=headings,
        text="\n".join(clean_lines),
        json_ld=json_ld,
    )


def select_internal_links(html: str, base_url: str, max_links: int = 2) -> list[str]:
    """Choose up to `max_links` high-signal same-domain URLs (/about, /team, /pricing, etc.)."""
    if max_links <= 0:
        return []

    soup = BeautifulSoup(html, "html.parser")
    base_parts = urllib.parse.urlsplit(base_url)
    base_domain = _strip_www(base_parts.hostname or "")
    base_path = base_parts.path.rstrip("/") or "/"

    candidates: dict[str, tuple[int, int, int]] = {}
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        resolved = urllib.parse.urljoin(base_url, href)
        parts = urllib.parse.urlsplit(resolved)
        if parts.scheme.lower() not in {"http", "https"}:
            continue

        cand_domain = _strip_www(parts.hostname or "")
        if cand_domain != base_domain:
            continue

        cand_path = parts.path.rstrip("/") or "/"
        if cand_path == base_path or cand_path.lower().endswith(_SKIP_EXTENSIONS):
            continue

        segments = [seg.lower() for seg in cand_path.split("/") if seg]
        if not segments or any(seg in _SKIP_SEGMENTS for seg in segments):
            continue

        best_score = max((_PRIORITY_TOKENS.get(seg, 0) for seg in segments), default=0)
        if best_score == 0:
            continue

        clean_url = urllib.parse.urlunsplit(
            parts._replace(scheme=parts.scheme.lower(), query="", fragment="")
        )
        ranking = (-best_score, len(segments), len(cand_path))
        prev_rank = candidates.get(clean_url)
        if prev_rank is None or ranking < prev_rank:
            candidates[clean_url] = ranking

    ordered = sorted(candidates.items(), key=lambda item: (item[1], item[0]))
    return [url for url, _ in ordered[:max_links]]


def _summarize_json_ld(records: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    interesting_keys = ("@type", "name", "description", "founder", "founders", "author", "creator")
    for record in records[:4]:
        compact = {k: record[k] for k in interesting_keys if k in record}
        if compact:
            lines.append(f"  JSON-LD: {json.dumps(compact, ensure_ascii=False)}")
    return lines


def build_structured_metadata(pages: list[ScrapedPage]) -> str:
    """Format extracted titles, meta descriptions, headings, and JSON-LD into compact text."""
    blocks: list[str] = []
    for page in pages:
        page_lines = [f"Page: {page.final_url}"]
        if page.title:
            page_lines.append(f"  Title: {page.title}")
        if page.meta_description:
            page_lines.append(f"  Meta Description: {page.meta_description}")
        if page.headings:
            page_lines.append(f"  Headings: {' | '.join(page.headings[:6])}")
        page_lines.extend(_summarize_json_ld(page.json_ld))
        blocks.append("\n".join(page_lines))
    return "\n\n".join(blocks)


def build_combined_text(pages: list[ScrapedPage], max_chars: int) -> str:
    """Combine cleaned text across fetched pages under a strict total character budget."""
    if not pages or max_chars <= 0:
        return ""

    if len(pages) == 1:
        budgets = [max_chars]
    else:
        primary_budget = int(max_chars * 0.55)
        secondary_budget = (max_chars - primary_budget) // (len(pages) - 1)
        budgets = [primary_budget] + [secondary_budget] * (len(pages) - 1)

    sections: list[str] = []
    remaining = max_chars
    for idx, page in enumerate(pages):
        if remaining <= 0:
            break
        header = f"--- SOURCE: {page.final_url} ---\n"
        if len(header) >= remaining:
            break
        body_text = page.text.strip()
        if not body_text:
            continue

        # Give the last page any unused character budget from shorter pages.
        alloc = remaining if idx == len(pages) - 1 else min(budgets[idx], remaining)
        available_body = alloc - len(header)
        if available_body <= 0:
            continue

        snippet = body_text[:available_body]
        section = f"{header}{snippet}"
        sections.append(section)
        remaining -= len(section) + 2  # account for "\n\n" separator

    return "\n\n".join(sections)[:max_chars]


async def _fetch_html(
    client: httpx.AsyncClient,
    url: str,
    settings: Settings,
    resolver: Callable[..., Any],
) -> tuple[str, str, int]:
    """Fetch a single URL safely with SSRF checks, byte caps, and bot-block detection."""
    parsed = urllib.parse.urlsplit(url)
    assert_public_host(parsed.hostname or "", resolver=resolver)

    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }

    try:
        async with client.stream(
            "GET",
            url,
            headers=headers,
            follow_redirects=True,
        ) as response:
            final_url = str(response.url)
            final_host = urllib.parse.urlsplit(final_url).hostname or ""
            assert_public_host(final_host, resolver=resolver)

            chunks: list[bytes] = []
            total_bytes = 0
            async for chunk in response.aiter_bytes():
                if not chunk:
                    continue
                remaining = settings.max_response_bytes - total_bytes
                if remaining <= 0:
                    break
                chunks.append(chunk[:remaining])
                total_bytes += min(len(chunk), remaining)
                if total_bytes >= settings.max_response_bytes:
                    break

            encoding = response.encoding or "utf-8"
            html = b"".join(chunks).decode(encoding, errors="replace")
            status = response.status_code

            if status in (403, 429) or _looks_like_bot_challenge(html):
                raise ScrapeError(
                    f"Target website blocked automated access (HTTP {status}).",
                    status if status in (403, 429) else 403,
                    "bot_blocked",
                )

            if status >= 400:
                raise ScrapeError(
                    f"Target website returned HTTP {status}.",
                    502,
                    "unreachable",
                )

            content_type = response.headers.get("content-type", "").lower()
            if content_type and not any(
                token in content_type for token in ("html", "text/", "xml")
            ):
                raise ScrapeError(
                    "Target URL did not return an HTML webpage.",
                    422,
                    "non_html",
                )

            return html, final_url, status
    except ScrapeError:
        raise
    except httpx.TimeoutException as exc:
        raise ScrapeError(
            f"Timed out waiting for '{url}' after {settings.http_timeout_seconds:.0f}s.",
            502,
            "unreachable",
        ) from exc
    except httpx.HTTPError as exc:
        raise ScrapeError(
            f"Failed to fetch '{url}': {exc}",
            502,
            "unreachable",
        ) from exc


async def scrape_site(
    raw_url: str,
    settings: Settings | None = None,
    client: httpx.AsyncClient | None = None,
    resolver: Callable[..., Any] = socket.getaddrinfo,
) -> ScrapedSite:
    """Fetch homepage + up to 2 high-signal pages and return structured text."""
    cfg = settings or get_settings()
    start = time.perf_counter()
    normalized_url = normalize_url(raw_url)

    owns_client = client is None
    http_client = client or httpx.AsyncClient(
        timeout=cfg.http_timeout_seconds,
        max_redirects=cfg.max_redirects,
        follow_redirects=True,
    )

    try:
        home_html, home_final_url, home_status = await _fetch_html(
            http_client, normalized_url, cfg, resolver
        )
        home_page = extract_page(home_html, normalized_url, home_final_url, home_status)
        pages: list[ScrapedPage] = [home_page]

        extra_urls = select_internal_links(
            home_html, home_final_url, max_links=cfg.max_extra_pages
        )
        if extra_urls:
            results = await asyncio.gather(
                *[
                    _fetch_html(http_client, extra_url, cfg, resolver)
                    for extra_url in extra_urls
                ],
                return_exceptions=True,
            )
            for extra_url, result in zip(extra_urls, results):
                if isinstance(result, Exception):
                    logger.info("Skipping secondary page %s: %s", extra_url, result)
                    continue
                extra_html, extra_final_url, extra_status = result
                pages.append(
                    extract_page(extra_html, extra_url, extra_final_url, extra_status)
                )

        structured_metadata = build_structured_metadata(pages)
        combined_text = build_combined_text(pages, max_chars=cfg.max_total_chars)
        total_clean_chars = sum(len(p.text.strip()) for p in pages)

        if total_clean_chars < cfg.min_usable_chars:
            raise ScrapeError(
                "Website returned too little readable HTML text (likely a JS-only SPA or empty shell).",
                422,
                "thin_content",
            )

        scrape_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "Scraped %s (%d pages, %d chars) in %d ms",
            normalized_url,
            len(pages),
            len(combined_text),
            scrape_ms,
        )
        return ScrapedSite(
            input_url=raw_url,
            normalized_url=normalized_url,
            pages=pages,
            structured_metadata=structured_metadata,
            combined_text=combined_text,
            extracted_chars=len(combined_text),
            scrape_ms=scrape_ms,
        )
    finally:
        if owns_client:
            await http_client.aclose()
