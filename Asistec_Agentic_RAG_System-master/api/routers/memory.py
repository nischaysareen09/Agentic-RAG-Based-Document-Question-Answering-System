# RAG_Chatbot/api/routers/memory.py

from fastapi import APIRouter, HTTPException, status, Query, Path
from typing import List

from api.schemas import memories as memory_schemas # Alias to avoid name clash
from core.mem0_client import mem0_client

router = APIRouter()

MEMORIES_PREFIX = "/memories"

@router.get(
    MEMORIES_PREFIX,
    response_model=memory_schemas.GetAllMemoriesResponse,
    summary="Get all memories for a user",
    description="Retrieves all long-term memories associated with a specific user ID from Mem0."
)
async def get_all_user_memories(
    user_id: str = Query(..., description="The ID of the user whose memories are to be retrieved.")
):
    if not mem0_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Mem0 client not initialized. Check API key.")
    
    try:
        memories_data = mem0_client.get_all(user_id=user_id)
        
        formatted_memories = []
        for mem_item in memories_data:
            formatted_memories.append(memory_schemas.MemoryItemResponse(
                id=mem_item['id'],
                memory=mem_item['memory'],
                user_id=mem_item['user_id'],
                created_at=mem_item['created_at'],
                updated_at=mem_item['updated_at']
            ))
        
        return memory_schemas.GetAllMemoriesResponse(memories=formatted_memories)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve memories: {e}")

@router.delete(
    MEMORIES_PREFIX + "/{memory_id}",
    response_model=memory_schemas.DeleteMemoryResponse,
    status_code=status.HTTP_200_OK, # Mem0 returns 200 OK for success
    summary="Delete a single memory by ID",
    description="Deletes a specific long-term memory item by its unique ID from Mem0."
)
async def delete_single_memory(
    memory_id: str = Path(..., description="The ID of the memory to delete.")
):
    if not mem0_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Mem0 client not initialized. Check API key.")
    
    try:
        response = mem0_client.delete(memory_id=memory_id)
        if response.get("message") == "Memory deleted successfully!":
            return memory_schemas.DeleteMemoryResponse(message=response["message"])
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Mem0 reported an issue: {response.get('message', 'Unknown error')}")

    except Exception as e:
        print(f"Error deleting memory {memory_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete memory: {e}")

@router.delete(
    MEMORIES_PREFIX + "/by_user/{user_id}",
    response_model=memory_schemas.DeleteAllUserMemoriesResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete all memories for a user",
    description="Deletes all memories associated with a specific user ID from Mem0."
)
async def delete_all_user_memories(
    user_id: str = Path(..., description="The ID of the user whose memories are to be deleted.")
):
    if not mem0_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Mem0 client not initialized. Check API key.")
    
    try:
        response = mem0_client.delete_all(user_id=user_id)
        if response.get("message") == "Memories deleted successfully!":
            return memory_schemas.DeleteAllUserMemoriesResponse(message=response["message"])
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Mem0 reported an issue: {response.get('message', 'Unknown error')}")

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete all memories: {e}")