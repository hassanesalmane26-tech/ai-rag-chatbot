from app.rag.vectorstore import vectorstore


def search_documents(query: str, k: int = 5):
    return vectorstore.similarity_search_with_relevance_scores(
        query,
        k=k,
    )
