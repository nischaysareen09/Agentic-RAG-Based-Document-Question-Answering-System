from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional
from database.models import UserRead as DBUserRead, ThreadRead as DBThreadRead, MessageRead as DBMessageRead

# --- User Schemas ---
class UserCreateRequestSchema(BaseModel):
    user_id: str 
    email: Optional[EmailStr] = None

class UserResponseSchema(DBUserRead): 
    pass


# --- Thread Schemas ---
class ThreadCreateRequestSchema(BaseModel):
    title: Optional[str] = "New Chat"

class ThreadResponseSchema(DBThreadRead):
    pass

class ThreadUpdateRequestSchema(BaseModel):
    title: str


# --- Message Schemas ---
class MessageCreateRequestSchema(BaseModel):
    content: str

class MessageResponseSchema(DBMessageRead):
    pass

class ChatResponseSchema(BaseModel):
    assistant_message: str
    thread_id: str
    new_message_id: int