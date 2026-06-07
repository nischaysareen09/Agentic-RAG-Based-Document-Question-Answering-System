from langchain_google_genai import ChatGoogleGenerativeAI

from core.config import settings

summarization_model = ChatGoogleGenerativeAI(
    model=settings.SUMMARY_MODEL, 
    api_key=settings.GOOGLE_API_KEY
    )

main_model = ChatGoogleGenerativeAI(
    model=settings.PRIMARY_MODEL,
    api_key=settings.GOOGLE_API_KEY
    )

scoring_model = ChatGoogleGenerativeAI(
    model=settings.SCORE_DOCUMENTS_MODEL,
    api_key=settings.GOOGLE_API_KEY,
    temperature=0.5
    )

rewriter_model = ChatGoogleGenerativeAI(
    model=settings.REWRITE_QUERY_MODEL,
    api_key=settings.GOOGLE_API_KEY,
    temperature=0.5
)