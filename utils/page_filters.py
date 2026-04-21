import re


def is_probably_toc_page(text: str) -> bool:
    if not text:
        return False
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 5:
        return False
    toc_like = 0
    for line in lines[:60]:
        if re.search(r".+\s+\d{1,3}$", line):
            toc_like += 1
    return toc_like >= 12


def is_probably_member_page(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    keywords = [
        "standards committee",
        "members",
        "member-secretary",
        "convenor",
        "acknowledgements",
        "personnel of the highways",
    ]
    hits = sum(1 for k in keywords if k in lower)
    return hits >= 3


def is_low_signal_page(text: str) -> bool:
    if not text:
        return True
    cleaned = text.strip()
    if len(cleaned) < 40:
        return True
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    numeric_short_lines = 0
    for line in lines[:80]:
        if re.fullmatch(r"[\d\.\-\,]+", line):
            numeric_short_lines += 1
    return numeric_short_lines >= 15


def should_skip_page(text: str) -> bool:
    return is_probably_toc_page(text) or is_probably_member_page(text) or is_low_signal_page(text)
