from __future__ import annotations

import re

DANGEROUS_PATTERNS = [
    r"\bdelete\b",
    r"\bremove\b",
    r"\bformat\b",
    r"\bwipe\b",
    r"\bshutdown\b",
    r"\bregistry\b",
    r"&&",
    r"\|\|",
    r";",
    r">\s",
]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def is_risky_text(value: str) -> bool:
    normalized = normalize_text(value)
    return any(re.search(pattern, normalized) for pattern in DANGEROUS_PATTERNS)

