import re
import unicodedata


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\x00", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_paragraphs(text: str, max_chars: int = 1800, overlap_paragraphs: int = 0):
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    if not paragraphs:
        return []

    chunks = []
    current = []

    for para in paragraphs:
        candidate = "\n\n".join(current + [para])
        if len(candidate) <= max_chars:
            current.append(para)
        else:
            if current:
                chunks.append("\n\n".join(current))

            overlap = current[-overlap_paragraphs:] if overlap_paragraphs > 0 else []
            current = overlap + [para]

            while len("\n\n".join(current)) > max_chars and len(current) > 1:
                current.pop(0)

    if current:
        chunks.append("\n\n".join(current))

    return chunks