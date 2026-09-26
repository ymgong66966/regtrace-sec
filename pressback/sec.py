from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .label import topic_similarity


EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
USER_AGENT = "PressBackResearch/0.1 contact=academic-research"


@dataclass(frozen=True)
class SecFiling:
    cik: str
    accession: str
    form: str
    file_date: str
    display_name: str
    file_numbers: list[str] | None = None

    @property
    def accession_nodash(self) -> str:
        return self.accession.replace("-", "")


@dataclass(frozen=True)
class SecDocument:
    filing: SecFiling
    url: str
    text: str


@dataclass(frozen=True)
class SecPair:
    cik: str
    display_name: str
    review_key: str
    review_file_no: str | None
    review_subject: str | None
    upload_accession: str
    response_accession: str
    upload_date: str
    response_date: str
    comment_index: int
    sec_comment: str
    company_response: str
    response_alignment_score: float | None
    response_alignment_method: str
    response_section_index: int | None
    label: str
    followup_comment_text: str | None
    followup_accession: str | None
    followup_date: str | None
    followup_topic_score: float | None
    issue_category: str

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"p", "br", "div", "tr", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        clean = data.strip()
        if clean:
            self.parts.append(clean)

    def text(self) -> str:
        return normalize_text(" ".join(self.parts))


def search_correspondence(
    startdt: str,
    enddt: str,
    size: int = 100,
    offset: int = 0,
    ciks: str | None = None,
    query: str | None = None,
) -> tuple[int, list[SecFiling]]:
    params = {
        "forms": "UPLOAD,CORRESP",
        "startdt": startdt,
        "enddt": enddt,
        "from": str(offset),
        "size": str(size),
    }
    if ciks:
        params["ciks"] = ciks
    if query:
        params["q"] = query
    data = fetch_json(EFTS_URL + "?" + urllib.parse.urlencode(params))
    hits = data.get("hits", {}).get("hits", [])
    total = data.get("hits", {}).get("total", {}).get("value", 0)
    filings = []
    for hit in hits:
        source = hit.get("_source", {})
        ciks = source.get("ciks") or []
        displays = source.get("display_names") or []
        file_numbers = _as_string_list(source.get("file_num") or source.get("file_nums"))
        if not ciks:
            continue
        filings.append(
            SecFiling(
                cik=str(ciks[0]).lstrip("0") or "0",
                accession=source["adsh"],
                form=source["form"],
                file_date=source["file_date"],
                display_name=displays[0] if displays else "",
                file_numbers=file_numbers or None,
            )
        )
    return total, filings


def download_filing_document(filing: SecFiling) -> SecDocument:
    base = f"{ARCHIVES}/{filing.cik}/{filing.accession_nodash}"
    index = fetch_json(f"{base}/index.json")
    names = [item["name"] for item in index.get("directory", {}).get("item", [])]
    preferred = choose_document_name(names, filing.form)
    url = f"{base}/{preferred}"
    raw = fetch_bytes(url)
    if preferred.lower().endswith(".pdf"):
        text = ""
    else:
        text = decode_document(raw, preferred)
    return SecDocument(filing=filing, url=url, text=text)


def choose_document_name(names: list[str], form: str) -> str:
    lower = [name.lower() for name in names]
    if form == "UPLOAD":
        for suffix in ("filename2.txt", "filename1.txt"):
            for name, lowered in zip(names, lower):
                if lowered.endswith(suffix):
                    return name
        for name, lowered in zip(names, lower):
            if lowered.endswith(".txt") and "-index" not in lowered:
                return name
    for ext in (".htm", ".html", ".txt"):
        for name, lowered in zip(names, lower):
            if lowered.startswith("filename") and lowered.endswith(ext):
                return name
    for name, lowered in zip(names, lower):
        if lowered.endswith(".txt") and "-index" not in lowered:
            return name
    raise ValueError(f"no usable document found among {names}")


@dataclass(frozen=True)
class ResponseSection:
    section_index: int
    raw_text: str
    response_text: str
    referenced_comment_numbers: list[int]


def build_pairs(
    documents: list[SecDocument],
    followup_threshold: float = 0.5,
    min_response_alignment: float = 0.12,
) -> list[SecPair]:
    by_thread: dict[str, list[SecDocument]] = {}
    for doc in documents:
        if doc.text.strip():
            key, _, _ = review_thread_key(doc)
            by_thread.setdefault(key, []).append(doc)
    pairs: list[SecPair] = []
    for review_key, docs in by_thread.items():
        ordered = sorted(docs, key=lambda doc: (doc.filing.file_date, _form_order(doc.filing.form), doc.filing.accession))
        for i, doc in enumerate(ordered):
            if doc.filing.form != "UPLOAD":
                continue
            response = _next_doc(ordered, i, "CORRESP")
            if response is None:
                continue
            next_upload = _next_doc(ordered, ordered.index(response), "UPLOAD")
            _, review_file_no, review_subject = review_thread_key(doc)
            comments = extract_numbered_items(doc.text)
            responses = extract_response_sections(response.text)
            used_response_sections: set[int] = set()
            for idx, comment in enumerate(comments, start=1):
                aligned = align_response_section(comment, idx, responses, used_response_sections)
                if aligned is None or aligned[2] < min_response_alignment:
                    continue
                section, alignment_method, alignment_score = aligned
                cleaned_response = strip_repeated_comment_prefix(section.response_text, comment)
                if len(cleaned_response.split()) < 8:
                    continue
                used_response_sections.add(section.section_index)
                followup, score = find_followup(comment, extract_numbered_items(next_upload.text) if next_upload else [], followup_threshold)
                pairs.append(
                    SecPair(
                        cik=doc.filing.cik,
                        display_name=doc.filing.display_name,
                        review_key=review_key,
                        review_file_no=review_file_no,
                        review_subject=review_subject,
                        upload_accession=doc.filing.accession,
                        response_accession=response.filing.accession,
                        upload_date=doc.filing.file_date,
                        response_date=response.filing.file_date,
                        comment_index=idx,
                        sec_comment=comment,
                        company_response=cleaned_response,
                        response_alignment_score=alignment_score,
                        response_alignment_method=alignment_method,
                        response_section_index=section.section_index,
                        label="unresolved" if followup else "resolved",
                        followup_comment_text=followup,
                        followup_accession=next_upload.filing.accession if followup and next_upload else None,
                        followup_date=next_upload.filing.file_date if followup and next_upload else None,
                        followup_topic_score=score,
                        issue_category=classify_issue(comment),
                    )
                )
    return pairs


def review_thread_key(doc: SecDocument) -> tuple[str, str | None, str | None]:
    file_no = first_file_number(doc.filing.file_numbers) or extract_file_number(doc.text)
    subject = extract_review_subject(doc.text)
    if file_no:
        return f"{doc.filing.cik}:file:{normalize_key(file_no)}", file_no, subject
    if subject:
        return f"{doc.filing.cik}:subject:{normalize_key(subject)[:120]}", None, subject
    return f"{doc.filing.cik}:unknown", None, None


def first_file_number(file_numbers: list[str] | None) -> str | None:
    if not file_numbers:
        return None
    for file_number in file_numbers:
        clean = normalize_text(str(file_number))
        if clean:
            return clean
    return None


def extract_file_number(text: str) -> str | None:
    clean = normalize_text(text)
    patterns = [
        r"\bFile\s+No\.?\s*[:#]?\s*([0-9]{3}-[0-9A-Za-z.-]+)",
        r"\bFile\s+Number\s*[:#]?\s*([0-9]{3}-[0-9A-Za-z.-]+)",
        r"\bFile\s*#\s*([0-9]{3}-[0-9A-Za-z.-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, clean, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .;:,")
    return None


def extract_review_subject(text: str) -> str | None:
    clean = normalize_text(text)
    match = re.search(
        r"\bRe:\s*(?P<subject>.{20,420}?)(?:\s+File\s+No\.|\s+Filed\s+|\s+Dear\s+|\s+Ladies\s+and\s+Gentlemen|$)",
        clean,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    subject = re.sub(r"\s+", " ", match.group("subject")).strip(" .;:,")
    if len(subject.split()) < 3:
        return None
    return subject


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def strip_repeated_comment_prefix(response_text: str, comment: str) -> str:
    text = normalize_text(response_text)
    comment_text = normalize_text(comment)
    if not text:
        return text

    response_match = re.search(
        r"\b(?:company\s+)?response\s*[:：]\s*",
        text,
        flags=re.IGNORECASE,
    )
    if response_match and response_match.start() <= max(500, len(comment_text) + 200):
        return text[response_match.end() :].strip(" -–—;:")

    common_tokens = _common_token_prefix(_tokenize_for_prefix(text), _tokenize_for_prefix(comment_text))
    if common_tokens >= 18:
        return _drop_token_prefix(text, common_tokens).strip(" -–—;:")

    if text.lower().startswith(comment_text[: min(len(comment_text), 180)].lower()):
        return text[len(comment_text) :].strip(" -–—;:")
    return text


def _tokenize_for_prefix(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9$%.-]+", text.lower())


def _common_token_prefix(left: list[str], right: list[str]) -> int:
    count = 0
    for left_token, right_token in zip(left, right):
        if left_token != right_token:
            break
        count += 1
    return count


def _drop_token_prefix(text: str, token_count: int) -> str:
    matches = list(re.finditer(r"[A-Za-z0-9$%.-]+", text))
    if token_count <= 0 or token_count > len(matches):
        return text
    return text[matches[token_count - 1].end() :]


def extract_numbered_items(text: str) -> list[str]:
    return [section for _, section in extract_numbered_sections(text)]


def extract_numbered_sections(text: str) -> list[tuple[int, str]]:
    clean = normalize_text(text)
    matches = list(re.finditer(r"(?:^|\s)(\d{1,2})\.\s+(?=[A-Z])", clean))
    sections: list[tuple[int, str]] = []
    for pos, match in enumerate(matches):
        start = match.end()
        end = matches[pos + 1].start() if pos + 1 < len(matches) else len(clean)
        item = clean_sec_comment_text(clean[start:end])
        if is_usable_sec_comment(item):
            sections.append((len(sections) + 1, item))
    return sections


def clean_sec_comment_text(text: str) -> str:
    clean = normalize_text(text).strip(" ;")
    clean = re.sub(r"\b(?:FirstName|LastName)\S*", " ", clean)
    clean = re.sub(r"\b(?:Comapany|Company)\s+Name\S*", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip(" ;")

    tail_patterns = [
        r"\bPlease contact [A-Z][A-Za-z .'-]+ at \d{3}-\d{3}-\d{4}.*$",
        r"\bIf you have questions regarding comments.*$",
        r"\bRefer to Rules 460 and 461 regarding requests for acceleration.*$",
        r"\bWe remind you that the company and its management are responsible for the accuracy and adequacy of their disclosures.*$",
        r"\bSincerely,.*$",
        r"\bcc:\s+.*$",
    ]
    for pattern in tail_patterns:
        clean = re.sub(pattern, "", clean, flags=re.IGNORECASE).strip(" ;")
    return re.sub(r"\s+", " ", clean).strip(" ;")


def is_usable_sec_comment(text: str) -> bool:
    clean = normalize_text(text)
    words = clean.split()
    if len(words) < 8:
        return False
    lowered = clean.lower()
    if lowered.startswith(("please contact ", "sincerely", "cc:")):
        return False
    if not re.search(
        r"\b(please|we note|tell us|revise|disclose|explain|provide|clarify|remove|present|file|address|advise|identify|reconcile)\b",
        lowered,
    ):
        return False
    if is_truncated_comment(clean):
        return False
    return True


def is_truncated_comment(text: str) -> bool:
    original = normalize_text(text).strip()
    clean = original.strip(" .;:,")
    if not clean:
        return True
    lowered = clean.lower()
    truncated_suffixes = (
        " on page",
        " page",
        " pages",
        " with",
        " to",
        " of",
        " the",
        " and",
        " or",
        " in",
        " for",
        " from",
        " at",
        " comment",
        " disclosure",
        " disclosures",
    )
    if lowered.endswith(truncated_suffixes):
        return True
    if len(clean.split()) < 20 and not original.endswith((".", "?", ":", ";", ")")):
        return True
    return False


def extract_response_sections(text: str) -> list[ResponseSection]:
    sections = []
    for section_index, raw in extract_numbered_sections(text):
        referenced = referenced_comment_numbers(raw)
        response_text = strip_response_label(raw)
        sections.append(
            ResponseSection(
                section_index=section_index,
                raw_text=raw,
                response_text=response_text,
                referenced_comment_numbers=referenced,
            )
        )
    if not sections:
        clean = normalize_text(text)
        sections.append(
            ResponseSection(
                section_index=1,
                raw_text=clean,
                response_text=strip_response_label(clean),
                referenced_comment_numbers=referenced_comment_numbers(clean),
            )
        )
    return sections


def align_response_section(
    comment: str,
    comment_index: int,
    sections: list[ResponseSection],
    used_sections: set[int] | None = None,
) -> tuple[ResponseSection, str, float] | None:
    if not sections:
        return None
    used_sections = used_sections or set()
    candidates = [section for section in sections if section.section_index not in used_sections] or sections

    for section in candidates:
        if comment_index in section.referenced_comment_numbers:
            return section, "explicit_comment_number", _alignment_score(comment, section.raw_text, section.response_text)

    local = next((section for section in candidates if section.section_index == comment_index), None)
    local_score = _alignment_score(comment, local.raw_text, local.response_text) if local else -1.0
    best = max(candidates, key=lambda section: _alignment_score(comment, section.raw_text, section.response_text))
    best_score = _alignment_score(comment, best.raw_text, best.response_text)

    if local and local_score >= max(0.25, best_score - 0.08):
        return local, "local_index_semantic", local_score
    return best, "semantic_best", best_score


def referenced_comment_numbers(text: str) -> list[int]:
    clean = normalize_text(text)
    head = clean[:500]
    numbers = []
    patterns = [
        r"\bresponse\s+to\s+(?:prior\s+)?comment\s+(\d{1,2})\b",
        r"\brespond(?:ing|s)?\s+to\s+(?:the\s+Staff'?s\s+)?(?:prior\s+)?comment\s+(\d{1,2})\b",
        r"\bwe\s+note\s+your\s+response\s+to\s+(?:our\s+)?(?:prior\s+)?comment\s+(\d{1,2})\b",
        r"\bas\s+previously\s+requested\b.*?\bcomment\s+(\d{1,2})\b",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, head, flags=re.IGNORECASE):
            numbers.append(int(match.group(1)))
    return sorted(set(numbers))


def strip_response_label(text: str) -> str:
    clean = normalize_text(text)
    match = re.search(r"\b(?:company\s+)?response\s*[:：]\s*", clean, flags=re.IGNORECASE)
    if match:
        return clean[match.end() :].strip(" -–—;:")
    return clean


def _alignment_score(comment: str, raw_section: str, response_text: str) -> float:
    raw_score = topic_similarity(comment, raw_section)
    response_score = topic_similarity(comment, response_text)
    return max(raw_score, response_score * 0.75)


def find_followup(comment: str, later_comments: list[str], threshold: float) -> tuple[str | None, float | None]:
    best_text = None
    best_score = 0.0
    for later in later_comments:
        score = topic_similarity(comment, later)
        if score > best_score:
            best_score = score
            best_text = later
    if best_text and best_score >= threshold:
        return best_text, best_score
    return None, None


def classify_issue(comment: str) -> str:
    lowered = comment.lower()
    if "non-gaap" in lowered or "non gaap" in lowered:
        return "non_gaap"
    if "revenue" in lowered or "recognition" in lowered or "contract" in lowered:
        return "revenue_recognition"
    if "risk factor" in lowered or "risks" in lowered:
        return "risk_factor"
    if "sponsor" in lowered or "business combination" in lowered or "spac" in lowered:
        return "spac_disclosure"
    if "cyber" in lowered:
        return "cybersecurity"
    if "crypto" in lowered or "digital asset" in lowered:
        return "crypto"
    return "other"


def write_filings_jsonl(filings: list[SecFiling], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(json.dumps(asdict(f), ensure_ascii=False) + "\n" for f in filings), encoding="utf-8")


def read_filings_jsonl(path: str | Path) -> list[SecFiling]:
    filings = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            filings.append(_filing_from_json(json.loads(line)))
    return filings


def write_documents_jsonl(documents: list[SecDocument], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for doc in documents:
        rows.append({"filing": asdict(doc.filing), "url": doc.url, "text": doc.text})
    destination.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def read_documents_jsonl(path: str | Path) -> list[SecDocument]:
    documents = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        documents.append(SecDocument(filing=_filing_from_json(row["filing"]), url=row["url"], text=row["text"]))
    return documents


def _filing_from_json(row: dict[str, Any]) -> SecFiling:
    return SecFiling(
        cik=str(row["cik"]),
        accession=row["accession"],
        form=row["form"],
        file_date=row["file_date"],
        display_name=row.get("display_name", ""),
        file_numbers=_as_string_list(row.get("file_numbers")),
    )


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[,;]", value) if part.strip()]
    return [str(value)]


def write_pairs_jsonl(pairs: list[SecPair], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(json.dumps(pair.to_json(), ensure_ascii=False) + "\n" for pair in pairs), encoding="utf-8")


def fetch_json(url: str) -> dict[str, Any]:
    return json.loads(fetch_bytes(url).decode("utf-8"))


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html,text/plain,*/*"})
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except Exception as exc:
            last_error = exc
            time.sleep(0.5 * (2**attempt))
    raise last_error or RuntimeError(f"failed to fetch {url}")


def decode_document(raw: bytes, name: str) -> str:
    text = raw.decode("utf-8", errors="replace")
    if name.lower().endswith((".htm", ".html")):
        parser = _TextExtractor()
        parser.feed(text)
        return parser.text()
    return normalize_text(text)


def normalize_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _next_doc(docs: list[SecDocument], start_index: int, form: str) -> SecDocument | None:
    for doc in docs[start_index + 1 :]:
        if doc.filing.form == form:
            return doc
    return None


def _form_order(form: str) -> int:
    if form == "UPLOAD":
        return 0
    if form == "CORRESP":
        return 1
    return 2


def download_documents(
    filings: list[SecFiling],
    delay: float = 0.2,
    limit: int | None = None,
    progress_every: int = 25,
) -> list[SecDocument]:
    documents = []
    selected = filings[:limit]
    for index, filing in enumerate(selected, start=1):
        try:
            documents.append(download_filing_document(filing))
        except Exception as exc:
            print(f"[warn] failed {filing.accession} {filing.form}: {exc}")
        if progress_every and (index % progress_every == 0 or index == len(selected)):
            print(f"[sec-download] {index}/{len(selected)} filings, downloaded={len(documents)}", flush=True)
        time.sleep(delay)
    return documents
