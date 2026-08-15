from app.rag.vectorstore import vectorstore


def search_documents(query: str, k: int = 5):
    return vectorstore.similarity_search_with_relevance_scores(
        query,
        k=k,
    )


def search_workspace_documents(workspace_id: str, query: str, k: int = 5):
    """Retrieve only Knowledge owned by the active Workspace."""
    return vectorstore.similarity_search_with_relevance_scores(
        query,
        k=k,
        filter={"workspace_id": workspace_id},
    )
