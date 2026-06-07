from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI

from pydantic import BaseModel, Field
from core.config import settings

# Function to format documents as a string of document Objects
def format_docs(docs: list[Document]) -> str:
    formatted_docs = "\n\n---\n\n".join(
        [
            f'<Document index={i} source="{doc.metadata["source"]}" page="{int(doc.metadata["page"])}"/>\n{doc.page_content}\n</Document>'
            for i, doc in enumerate(docs)
        ]
    )
    return formatted_docs


class Title(BaseModel):
    title: str = Field(..., description="The title based on user message.")


async def generate_thead_title(message: str) -> str:
    title = await (
        ChatGoogleGenerativeAI(
            model=settings.THREAD_TITLE_GENERATOR_MODEL,
            api_key=settings.GOOGLE_API_KEY,
            temperature=0.2,
        )
        .with_structured_output(Title)
        .ainvoke(
            "Generate a 4-5 words title based on the following user message. \nUser Message: "
            + message
        )
    )
    return title.title