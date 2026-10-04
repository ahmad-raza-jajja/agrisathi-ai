"""Documents -> text -> clean -> chunk.  (Embedding + index happen in retriever.py, in memory.)

Add .md / .txt / .pdf files to data/documents/. Optional first lines of text files:
    TITLE: ...      SOURCE: ...   (publisher / URL shown to the farmer)
Inspect the chunks:  python -m rag.ingest
"""
import re
from pathlib import Path
from typing import List

from utils import config


def read_document(path: Path) -> dict:
    title, source = path.stem.replace("_", " "), path.name
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        text = "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    else:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        start = 0
        for i, line in enumerate(lines[:6]):
            if line.upper().startswith("TITLE:"):
                title, start = line.split(":", 1)[1].strip(), i + 1
            elif line.upper().startswith("SOURCE:"):
                source, start = line.split(":", 1)[1].strip(), i + 1
        text = "\n".join(lines[start:])
    return {"file": path.name, "title": title, "source": source, "text": clean(text)}


def clean(text: str) -> str:
    text = text.replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def chunk(text: str, size: int, overlap: int) -> List[str]:
    paras = [p.split() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, cur = [], []
    for para in paras:
        if cur and len(cur) + len(para) > size:
            chunks.append(" ".join(cur))
            cur = cur[-overlap:] if overlap else []
        cur.extend(para)
        while len(cur) > size * 1.5:
            chunks.append(" ".join(cur[:size]))
            cur = cur[size - overlap:]
    if cur:
        chunks.append(" ".join(cur))
    return [c for c in chunks if len(c.split()) >= 12]


def load_chunks(docs_dir: Path = None) -> List[dict]:
    docs_dir = Path(docs_dir or config.DOCS_DIR)
    files = sorted(p for p in docs_dir.glob("*") if p.suffix.lower() in {".md", ".txt", ".pdf"})
    records = []
    for f in files:
        doc = read_document(f)
        for i, c in enumerate(chunk(doc["text"], config.CHUNK_WORDS, config.CHUNK_OVERLAP), 1):
            records.append({"id": f"{f.stem}#{i}", "file": doc["file"], "title": doc["title"],
                            "source": doc["source"], "text": c})
    return records


if __name__ == "__main__":
    recs = load_chunks()
    print(f"{len(recs)} chunks from {len({r['file'] for r in recs})} documents")
    for r in recs:
        print(f"- {r['id']}: {len(r['text'].split())} words")
