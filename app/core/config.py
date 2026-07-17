from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI RAG Chatbot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    OPENAI_API_KEY: str = ""
    DATABASE_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
