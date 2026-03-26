from pathlib import Path
from typing import Optional
from pypdf import PdfReader


def read_txt_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return {
        "document_name": path.name,
        "source_type": "txt",
        "pages": [
            {
                "page_number": None,
                "text": text
            }
        ]
    }


def read_pdf_file(path: Path) -> dict:
    reader = PdfReader(str(path))
    pages = []

    for i, page in enumerate(reader.pages, start=1):
        pages.append({
            "page_number": i,
            "text": page.extract_text() or ""
        })

    return {
        "document_name": path.name,
        "source_type": "pdf",
        "pages": pages
    }


def read_document(path: Path) -> Optional[dict]:
    if path.suffix.lower() == ".txt":
        return read_txt_file(path)
    elif path.suffix.lower() == ".pdf":
        return read_pdf_file(path)
    return None


def load_documents(data_dir: str):
    documents = []

    for path in Path(data_dir).glob("*"):
        doc = read_document(path)
        if doc is not None:
            documents.append(doc)

    return documents