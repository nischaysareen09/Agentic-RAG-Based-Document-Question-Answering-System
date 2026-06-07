from langchain_core.tools import tool
from core.vectorstore import pc_store
from utils.helper import format_docs

@tool
def retrieve_documents(query: str, top_k: int = 5) -> str:
    """Retrieve documents from the vector store based on a Spanish query.

    Args:
        query (str): The query to retrieve documents for.
        top_k (int, optional): The number of top documents to retrieve. Defaults to 5.

    Returns:
        str: The retrieved documents formatted as a merged string.
    """
    results = pc_store.similarity_search(query, k=top_k)
    context = format_docs(results)
    return context

tools = [retrieve_documents]
tools_by_name = {tool.name: tool for tool in tools}