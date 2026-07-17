from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


embeddings = OpenAIEmbeddings(
    api_key=settings.OPENAI_API_KEY,
    model="text-embedding-3-small",
)
