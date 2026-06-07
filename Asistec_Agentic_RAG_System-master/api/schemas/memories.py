from pydantic import BaseModel, Field as PydanticField, ConfigDict
from datetime import datetime
from typing import List, Optional

class MemoryItemResponse(BaseModel):
    """Schema for a single memory item returned from Mem0."""
    id: str = PydanticField(..., description="Unique ID of the memory.")
    memory: str = PydanticField(..., description="The content of the memory.")
    user_id: str = PydanticField(..., description="The ID of the user this memory belongs to.")
    created_at: datetime = PydanticField(..., description="Timestamp when the memory was created.")
    updated_at: datetime = PydanticField(..., description="Timestamp when the memory was last updated.")

    model_config = ConfigDict(from_attributes=True) 


class GetAllMemoriesResponse(BaseModel):
    """Schema for returning a list of memories for a user."""
    memories: List[MemoryItemResponse] = PydanticField(default_factory=list, description="List of memory items.")

class DeleteMemoryResponse(BaseModel):
    """Schema for confirming a memory deletion."""
    message: str = PydanticField(..., json_schema_extra={'example': "Memory deleted successfully!"})

class DeleteAllUserMemoriesResponse(BaseModel):
    """Schema for confirming deletion of all memories for a user."""
    message: str = PydanticField(..., json_schema_extra={'example': "Memory deleted successfully!"})