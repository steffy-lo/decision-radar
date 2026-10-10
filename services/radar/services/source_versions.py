"""Stable identifiers and exact quote locations for immutable source text."""

from dataclasses import dataclass
from hashlib import sha256

NORMALIZER_VERSION = "plain_text_v1"


def normalize_text(text: str) -> str:
    """Keep user-visible characters stable while normalising line endings."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def version_id(source_id: str, text: str) -> str:
    digest = sha256(normalize_text(text).encode("utf-8")).hexdigest()
    return "ver_" + sha256(f"{source_id}:{NORMALIZER_VERSION}:{digest}".encode()).hexdigest()[:32]


@dataclass(frozen=True)
class CanonicalSpan:
    id: str
    version_id: str
    start: int
    end: int
    quote: str
    locator: str
    line: int
    column: int


def resolve_quote(source_id: str, text: str, quote: str, *, document: bool = False) -> CanonicalSpan:
    snapshot = normalize_text(text)
    if not quote or not quote.strip():
        raise ValueError("candidate has no evidence quote")
    start = snapshot.find(quote)
    if start < 0:
        raise ValueError("evidence quote is absent from the source snapshot")
    if snapshot.find(quote, start + 1) >= 0:
        raise ValueError("evidence quote matches more than one source span")
    end = start + len(quote)
    vid = version_id(source_id, snapshot)
    digest = sha256(f"{vid}:{NORMALIZER_VERSION}:{start}:{end}".encode()).hexdigest()[:32]
    line = snapshot.count("\n", 0, start) + 1
    prior_break = snapshot.rfind("\n", 0, start)
    column = start - prior_break
    structure = "Paragraph" if document else "Line"
    locator = f"{structure} {line}, character {column}; snapshot characters {start + 1}–{end}"
    return CanonicalSpan(f"span_{digest}", vid, start, end, quote, locator, line, column)
