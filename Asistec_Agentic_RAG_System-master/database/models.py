import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, Column, DateTime, String
from sqlalchemy.sql import func
from sqlalchemy import Text
from enum import Enum

# --- User Model ---
class UserBase(SQLModel):
    user_id: str = Field(primary_key=True, index=True, nullable=False)
    email: Optional[str] = Field(default=None, unique=True, index=True, nullable=True)

class User(UserBase, table=True):
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    threads: List["Thread"] = Relationship(back_populates="user")

class UserCreate(SQLModel): # Schema for creating a user
    user_id: str # Client must provide this
    email: Optional[str] = None

class UserRead(UserBase): # Schema for reading a user
    created_at: datetime

# --- Thread Model ---
class ThreadBase(SQLModel):
    title: str = Field(default="New Chat")
    user_id: str = Field(foreign_key="user.user_id", index=True) # Foreign key to User.user_id (string)

class Thread(ThreadBase, table=True):
    __tablename__ = "threads"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )

    user: Optional[User] = Relationship(back_populates="threads")
    messages: List["Message"] = Relationship(
        back_populates="thread",
        sa_relationship_kwargs={"order_by": "Message.timestamp", "cascade": "all, delete-orphan"}
    )


class ThreadCreate(ThreadBase):
    pass

class ThreadRead(ThreadBase):
    id: str
    created_at: datetime
    updated_at: datetime

class ThreadUpdate(SQLModel):
    title: Optional[str] = None


# --- Message Model --- 
class MessageBase(SQLModel):
    role: str
    content: str
    thread_id: str = Field(foreign_key="threads.id", index=True)

class Message(MessageBase, table=True):
    __tablename__ = "messages"
    id: Optional[int] = Field(default=None, primary_key=True, index=True) # Auto-incrementing int for messages
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    thread: Optional[Thread] = Relationship(back_populates="messages")

class MessageCreate(MessageBase):
    pass

class MessageRead(MessageBase):
    id: int
    timestamp: datetime

# --- Models for Upload Job Status ---
class FileProcessingStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class UploadJobBase(SQLModel):
    overall_status: FileProcessingStatusEnum = Field(default=FileProcessingStatusEnum.PENDING, index=True)

class UploadJob(UploadJobBase, table=True):
    __tablename__ = "upload_jobs"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now()))
    
    files: List["FileProcessingAttempt"] = Relationship(back_populates="job", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class FileProcessingAttemptBase(SQLModel):
    filename: str = Field(index=True)
    status: FileProcessingStatusEnum = Field(default=FileProcessingStatusEnum.PENDING, index=True)
    message: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    chunks_indexed: Optional[int] = Field(default=None)
    job_id: str = Field(foreign_key="upload_jobs.id")

class FileProcessingAttempt(FileProcessingAttemptBase, table=True):
    __tablename__ = "file_processing_attempts"
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    
    job: Optional[UploadJob] = Relationship(back_populates="files")

# Update forward references
User.model_rebuild()
Thread.model_rebuild()
Message.model_rebuild()
UploadJob.model_rebuild()
FileProcessingAttempt.model_rebuild()

def create_db_and_tables(engine_to_use):
    SQLModel.metadata.create_all(engine_to_use)