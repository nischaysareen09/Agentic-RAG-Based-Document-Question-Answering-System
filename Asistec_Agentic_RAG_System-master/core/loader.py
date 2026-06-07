from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
import tempfile
import os
from typing import List

async def load_pdf_from_bytes(file_bytes: bytes, filename: str) -> List[Document]:
    """
    Loads PDF content from bytes using PyPDFLoader.
    Each page of the PDF is returned as a separate Langchain Document,
    with specific metadata: "source" (original filename) and "page" (page number).
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(file_bytes)
        temp_file_path = temp_file.name
    
    processed_documents: List[Document] = []
    try:
        loader = PyPDFLoader(temp_file_path)
        raw_page_documents = loader.load() 
        
        for i, page_doc in enumerate(raw_page_documents):
            # Extract existing metadata or initialize if None
            current_metadata = page_doc.metadata if page_doc.metadata is not None else {}
            
            page_number_from_loader = current_metadata.get("page") # PyPDFLoader specific
            
            if page_number_from_loader is not None:
                page_number = int(page_number_from_loader) + 1 
            else:
                page_number = i + 1

            # Create a new Document with refined metadata to ensure structure
            processed_doc = Document(
                page_content=page_doc.page_content,
                metadata={
                    "source": filename, 
                    "page": page_number 
                }
            )
            processed_documents.append(processed_doc)
            
    except Exception as e:
        print(f"Error loading PDF {filename} using PyPDFLoader: {e}")
        raise
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
    return processed_documents
