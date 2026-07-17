from langchain_community.vectorstores import FAISS

from app.rag.embeddings import embeddings


def create_vectorstore(documents):
    return FAISS.from_documents(
        documents,
        embeddings,
    )
