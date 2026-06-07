from langchain_openai import OpenAIEmbeddings
import os
from .config import settings

def get_embedding_model() -> OpenAIEmbeddings:
    """Get an instance of a OpenAI embedding model"""

    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
    )
