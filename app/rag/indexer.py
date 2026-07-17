from pathlib import Path

from app.rag.loader import load_document
from app.rag.splitter import split_documents
from app.rag.vectorstore import vectorstore


DOCUMENTS_DIR = "documents"


def index_documents():
    files = Path(DOCUMENTS_DIR).glob("*")

    total = 0

    for file in files:
        print(f"Indexation de {file.name}...")

        docs = load_document(str(file))
        chunks = split_documents(docs)

        vectorstore.add_documents(chunks)

        total += len(chunks)

    print(f"{total} morceaux indexés.")


if __name__ == "__main__":
    index_documents()
