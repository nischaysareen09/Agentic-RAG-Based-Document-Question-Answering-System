import os
from dotenv import load_dotenv
_ = load_dotenv()

from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document

import asyncio
from typing import List
from tenacity import retry, wait_exponential, stop_after_attempt, before_log

from .config import settings
from .embeddings import get_embedding_model

pc = Pinecone(api_key=settings.PINECONE_API_KEY)

index_name = settings.PINECONE_INDEX_NAME
index = pc.Index(index_name)

pc_store = PineconeVectorStore(
    index=index, 
    namespace=settings.NAMESPACE, 
    embedding=get_embedding_model()
    )

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=20),
    stop=stop_after_attempt(5),
    before_sleep=before_log("Retrying add_documents_to_vector_store", __import__("logging").getLogger(__name__)), # Log retries
    reraise=True
)
async def _add_documents_batch_with_retry(
    vector_store: PineconeVectorStore, 
    batch: List[Document], 
    index_name: str
) -> List[str]:
    """Helper function to add a single batch of documents with retries."""
    print(f"Attempting to add batch of {len(batch)} documents to Pinecone index '{index_name}'...")
    ids = await vector_store.aadd_documents(batch)
    print(f"Successfully added batch of {len(ids)} documents.")
    return ids

async def add_documents_to_vector_store(
    documents: List[Document], 
    index_name: str = settings.PINECONE_INDEX_NAME,
    batch_size: int = 100 # Observed limit 100-150, so use 100 for safety
):
    """
    Adds documents to the vector store in batches with retries and delays.
    """
    if not documents:
        print("No documents to add to vector store.")
        return []

    all_indexed_ids = []

    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        try:
            indexed_ids = await _add_documents_batch_with_retry(pc_store, batch, index_name)
            all_indexed_ids.extend(indexed_ids)
            await asyncio.sleep(2) # Small delay between batches to respect rate limits
        except Exception as e:
            print(f"Fatal error after retries for batch starting at index {i}: {e}")
            raise

    print(f"Added {len(all_indexed_ids)} total document chunks to Pinecone index '{index_name}'.")
    return all_indexed_ids
