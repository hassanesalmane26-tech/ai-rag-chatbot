from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


embeddings = OpenAIEmbeddings(
    api_key=settings.openai_key(),
    model=settings.openai_embedding_model,
    request_timeout=settings.provider_timeout_seconds,
)
