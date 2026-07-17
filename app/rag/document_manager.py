from pathlib import Path
import shutil

from app.rag.loader import load_document
from app.rag.splitter import split_documents
from app.rag.vectorstore import vectorstore

DOCUMENTS_DIR = Path("documents")


def list_documents():
    DOCUMENTS_DIR.mkdir(exist_ok=True)

    return [
        file.name
        for file in DOCUMENTS_DIR.iterdir()
        if file.is_file()
    ]


def rebuild_index():
    DOCUMENTS_DIR.mkdir(exist_ok=True)

    vectorstore.reset_collection()

    total = 0

    for file in DOCUMENTS_DIR.iterdir():

        if not file.is_file():
            continue

        docs = load_document(str(file))
        chunks = split_documents(docs)

        vectorstore.add_documents(chunks)

        total += len(chunks)

    return total


def save_document(upload_file):
    DOCUMENTS_DIR.mkdir(exist_ok=True)

    destination = DOCUMENTS_DIR / upload_file.filename

    with open(destination, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return destination


def delete_document(filename):
    file = DOCUMENTS_DIR / filename

    if file.exists():
        file.unlink()

    rebuild_index()
