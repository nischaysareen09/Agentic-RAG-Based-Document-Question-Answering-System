from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List

def split_documents(
    documents: List[Document], 
    chunk_size: int = 1000,
) -> List[Document]:
    """Splits a list of Langchain Documents into smaller chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        separators=["\n\n", "\n", ".", ",", " "],
        chunk_overlap=chunk_size * 0.15,  # 15% overlap
        length_function=len,
    )
    chunks = text_splitter.split_documents(documents)
    return chunks