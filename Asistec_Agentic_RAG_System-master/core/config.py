from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_file_encoding="utf-8"
    )
    # --- Application Configuration ---
    APP_NAME: str = "RAG Backend"
    APP_VERSION: str = "0.1.0"
    ALLOWED_ORIGINS: list = ["*"]
    
    # --- Database Configuration ---
    DATABASE_URL: str
    DB_CONNECT_ARGS: dict = {"sslmode": "require"}
    
    # --- Mem0 Configuration ---
    MEM0_API_KEY: str

    # --- Google Models Configuration ---
    GOOGLE_API_KEY: str
    PRIMARY_MODEL: str = "gemini-2.5-flash-preview-05-20"

    SUMMARY_MODEL: str = "gemini-2.0-flash"
    REWRITE_QUERY_MODEL: str = "gemini-2.0-flash"
    SCORE_DOCUMENTS_MODEL: str = "gemini-2.0-flash"
    THREAD_TITLE_GENERATOR_MODEL: str = "gemini-2.0-flash-lite"

    # --- Pinecone Configuration ---
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str
    NAMESPACE: str = "rag"

    # --- Agents Configuration ---
    MESSAGES_SUMMARY_TRIGGER: int = 2000
    MAX_SUMMARY_TOKENS: int = 500
    MAX_TOKENS : int = 600
    MAX_RETRIEVAL_LOOP_COUNT: int = 2
    SCORE_THRESHOLD: int = 6
    
    # --- RAG Configuration ---
    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    EMBEDDING_MODEL_DIM: int = 3072
    TASK_TYPE: str = "RETRIEVAL_DOCUMENT"
    CHUNK_SIZE: int = 1000


settings = Settings()