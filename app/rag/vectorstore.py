from langchain_chroma import Chroma

from app.core.config import settings
from app.rag.embeddings import embeddings


vectorstore = Chroma(
    persist_directory=str(settings.vector_db_path),
    embedding_function=embeddings,
)
