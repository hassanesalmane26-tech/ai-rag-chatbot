from langchain_chroma import Chroma

from app.rag.embeddings import embeddings


VECTOR_DB_PATH = "vector_db"


vectorstore = Chroma(
    persist_directory=VECTOR_DB_PATH,
    embedding_function=embeddings,
)
