from datetime import datetime
from pydantic import BaseModel, Field as PydanticField, ConfigDict 
from typing import List, Optional, Dict, Any
from database.models import FileProcessingStatusEnum

class UploadFileResponse(BaseModel):
    job_id: Optional[str] = None 
    status: str = PydanticField(..., json_schema_extra={'example': "accepted"})
    message: str = PydanticField(..., json_schema_extra={'example': "Files accepted for processing."})
    files_scheduled: List[str] = PydanticField(default_factory=list, json_schema_extra={'example': ["document1.pdf"]})
    files_rejected: List[str] = PydanticField(default_factory=list)

class FileStatusResponseItem(BaseModel):
    filename: str
    status: FileProcessingStatusEnum # Use the DB Enum
    message: Optional[str] = None
    chunks_indexed: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    job_id: str = PydanticField(..., alias='id')
    overall_status: FileProcessingStatusEnum 
    created_at: datetime 
    updated_at: Optional[datetime] 
    files: List[FileStatusResponseItem]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)