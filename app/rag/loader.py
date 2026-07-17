from pathlib import Path

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
)


def load_document(file_path: str):
    path = Path(file_path)

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        loader = PyPDFLoader(file_path)

    elif suffix == ".docx":
        loader = Docx2txtLoader(file_path)

    elif suffix == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")

    else:
        raise ValueError(f"Format non supporté : {suffix}")

    return loader.load()
