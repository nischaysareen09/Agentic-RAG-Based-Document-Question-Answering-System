from typing import List, Optional, Dict
from core.loader import load_pdf_from_bytes
from core.splitter import split_documents
from core.vectorstore import add_documents_to_vector_store

async def process_and_index_pdf(
    file_bytes: bytes, 
    filename: str, 
    custom_metadata: Optional[Dict] = None
) -> int:
    """
    Processes a PDF file from bytes, splits it into chunks, 
    and indexes the chunks into the vector store.
    Returns the number of chunks indexed. Handles large files and rate limits internally.
    """
    print(f"Starting processing for PDF: {filename}")
    
    # 1. Load PDF into documents (each page is a Document)
    documents = await load_pdf_from_bytes(file_bytes, filename)
    if not documents:
        print(f"No documents loaded from {filename}. File might be empty or corrupted.")
        return 0
    print(f"Loaded {len(documents)} pages from {filename}.")

    # 2. Add any custom metadata to all loaded documents (pages)
    # Also add page number metadata
    for i, page in enumerate(documents):
        page.metadata["source"] = filename
        page.metadata["file_name"] = filename
        page.metadata["page"] = i + 1 # Add page number
        if custom_metadata:
            page.metadata.update(custom_metadata)
    
    # 3. Split documents into manageable chunks
    chunks = split_documents(documents)
    if not chunks:
        print(f"No chunks created from {filename}. File content might be too small or formatting issue.")
        return 0
    print(f"Split into {len(chunks)} chunks for {filename}.")

    # 4. Add chunks to vector store (Pinecone) with batching and retries
    try:
        indexed_ids = await add_documents_to_vector_store(chunks)
        num_indexed = len(indexed_ids) if indexed_ids else 0
        print(f"Successfully indexed {num_indexed} chunks from {filename}.")
        return num_indexed
    except Exception as e:
        print(f"Critical error during indexing for {filename}: {e}")
        # Re-raise to let the router know this file failed completely
        raise