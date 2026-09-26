from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path


BASE_URL = "https://www.fool.com"
LISTING_URL = "https://www.fool.com/earnings-call-transcripts/"
USER_AGENT = "PressBackResearch/0.1 contact=academic-research"


@dataclass(frozen=True)
class FoolArticle:
    url: str
    title: str
    ticker: str | None
    date_line: str | None
    transcript_text: str


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._href: str | None = None
        self._text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            text = " ".join(part.strip() for part in self._text if part.strip())
            self.links.append((self._href, text))
            self._href = None
            self._text = []


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"p", "br", "div", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        clean = data.strip()
        if clean:
            self.parts.append(clean)

    def text(self) -> str:
        raw = " ".join(self.parts)
        raw = re.sub(r"\s*\n\s*", "\n", raw)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{2,}", "\n", raw)
        return raw.strip()


def discover_transcript_urls(pages: int = 1, delay: float = 0.5) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for page in range(1, pages + 1):
        url = LISTING_URL if page == 1 else urllib.parse.urljoin(LISTING_URL, f"page/{page}/")
        parser = _AnchorParser()
        parser.feed(fetch_url(url))
        for href, text in parser.links:
            if "Earnings" not in text or "Transcript" not in text:
                continue
            full_url = urllib.parse.urljoin(BASE_URL, href)
            if "/earnings/call-transcripts/" not in full_url:
                continue
            if full_url not in seen:
                seen.add(full_url)
                found.append((full_url, text))
        time.sleep(delay)
    return found


def fetch_fool_article(url: str) -> FoolArticle:
    text = html_to_text(fetch_url(url))
    title = _extract_title(text)
    transcript = _extract_transcript_section(text)
    return FoolArticle(
        url=url,
        title=title,
        ticker=_ticker_from_title(title),
        date_line=_extract_after_heading(text, "DATE"),
        transcript_text=transcript,
    )


def write_fool_articles(urls: list[tuple[str, str]], output_dir: str | Path, delay: float = 1.0) -> list[FoolArticle]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    articles: list[FoolArticle] = []
    for url, fallback_title in urls:
        article = fetch_fool_article(url)
        title = article.title or fallback_title
        article = FoolArticle(
            url=article.url,
            title=title,
            ticker=article.ticker or _ticker_from_title(title),
            date_line=article.date_line,
            transcript_text=article.transcript_text,
        )
        (destination / f"{_safe_stem(title)}.txt").write_text(article.transcript_text + "\n", encoding="utf-8")
        articles.append(article)
        time.sleep(delay)
    manifest = [asdict(article) | {"transcript_text": ""} for article in articles]
    (destination / "manifest.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manifest),
        encoding="utf-8",
    )
    return articles


def fetch_url(url: str, timeout: int = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        encoding = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(encoding, errors="replace")


def html_to_text(html: str) -> str:
    parser = _TextParser()
    parser.feed(html)
    return parser.text()


def _extract_transcript_section(text: str) -> str:
    marker = "Full Conference Call Transcript"
    start = text.find(marker)
    if start == -1:
        raise ValueError("Could not find Full Conference Call Transcript section")
    body = text[start + len(marker) :]
    for end_marker in ["Read Next", "This article is a transcript", "Stocks Mentioned"]:
        end = body.find(end_marker)
        if end != -1:
            body = body[:end]
            break
    return "\n".join(line.strip() for line in body.splitlines() if line.strip())


def _extract_title(text: str) -> str:
    match = re.search(r"([^\n]+Earnings(?: Call)? Transcript)", text)
    return match.group(1).strip() if match else ""


def _extract_after_heading(text: str, heading: str) -> str | None:
    match = re.search(rf"{re.escape(heading)}\n([^\n]+)", text)
    return match.group(1).strip() if match else None


def _ticker_from_title(title: str) -> str | None:
    match = re.search(r"\(([A-Z.:-]{1,8})\)", title)
    return match.group(1) if match else None


def _safe_stem(text: str) -> str:
    return (re.sub(r"[^a-zA-Z0-9._-]+", "_", text.lower()).strip("_") or "transcript")[:120]

