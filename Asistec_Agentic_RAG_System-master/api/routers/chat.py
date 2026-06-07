from fastapi import APIRouter, Depends, HTTPException, status, Path, Body, Query, Response
from sqlmodel import Session
from typing import List

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from database import crud, models
from database.database import get_db

from api.schemas import chat as chat_schemas

from workflow.graph import graph as compiled_rag_graph
from utils.helper import generate_thead_title

router = APIRouter()

# --- User Endpoints ---
@router.post("/users", response_model=chat_schemas.UserResponseSchema, status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_new_user(
    user_in: chat_schemas.UserCreateRequestSchema,
    db: Session = Depends(get_db)
):
    try:
        created_user = crud.create_user(db, models.UserCreate(user_id=user_in.user_id, email=user_in.email))
        return created_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/users/{user_id}", response_model=chat_schemas.UserResponseSchema, tags=["Users"])
def get_user_details(
    user_id: str = Path(..., description="The string ID of the user to retrieve"),
    db: Session = Depends(get_db)
):
    db_user = crud.get_user_by_user_id(db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user


# --- Thread Endpoints ---
class ThreadCreateWithUserSchema(chat_schemas.ThreadCreateRequestSchema):
    user_id: str

@router.post("/threads", response_model=chat_schemas.ThreadResponseSchema, status_code=status.HTTP_201_CREATED, tags=["Threads"])
def create_new_thread(
    thread_in: ThreadCreateWithUserSchema, # Expects user_id in body
    db: Session = Depends(get_db)
):
    db_user = crud.get_user_by_user_id(db, user_id=thread_in.user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id '{thread_in.user_id}' not found.")
    
    created_thread = crud.create_thread_for_user(db, user_id=thread_in.user_id, title=thread_in.title)
    return created_thread

@router.get("/threads", response_model=List[chat_schemas.ThreadResponseSchema], tags=["Threads"])
def get_all_threads_for_a_user(
    user_id: str = Query(..., description="The string ID of the user whose threads to retrieve"),
    db: Session = Depends(get_db)
):
    db_user = crud.get_user_by_user_id(db, user_id=user_id)
    if not db_user:
   
        return []
    
    threads = crud.get_threads_for_user(db, user_id=user_id)
    return threads

@router.get("/threads/{thread_id}", response_model=chat_schemas.ThreadResponseSchema, tags=["Threads"])
def get_single_thread(
    thread_id: str = Path(..., description="The ID of the thread to retrieve"),
    db: Session = Depends(get_db)
):
    db_thread = crud.get_thread_by_id(db, thread_id=thread_id)
    if not db_thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
   
    return db_thread

@router.patch("/threads/{thread_id}", response_model=chat_schemas.ThreadResponseSchema, tags=["Threads"])
def update_thread_title(
    thread_id: str = Path(..., description="The ID of the thread to update"),
    thread_update_in: chat_schemas.ThreadUpdateRequestSchema = Body(...),
    db: Session = Depends(get_db)
):
    db_thread = crud.get_thread_by_id(db, thread_id=thread_id)
    if not db_thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    updated_thread = crud.update_thread(db, thread_id=thread_id, thread_update=models.ThreadUpdate(title=thread_update_in.title))
    return updated_thread

@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Threads"])
def delete_a_thread(
    thread_id: str = Path(..., description="The ID of the thread to delete"),
    db: Session = Depends(get_db)
):
    db_thread = crud.get_thread_by_id(db, thread_id=thread_id)
    if not db_thread:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if not crud.delete_thread(db, thread_id=thread_id):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete thread")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Message Endpoints (Chat Interaction) ---
@router.get("/threads/{thread_id}/messages", response_model=List[chat_schemas.MessageResponseSchema], tags=["Messages"])
def get_messages_in_a_thread(
    thread_id: str = Path(..., description="The ID of the thread"),
    db: Session = Depends(get_db)
):
    db_thread = crud.get_thread_by_id(db, thread_id=thread_id)
    if not db_thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    messages = crud.get_messages_for_thread(db, thread_id=thread_id)
    return messages

# Schema for sending a message now needs user_id in the body
class MessageCreateWithUserSchema(chat_schemas.MessageCreateRequestSchema):
    user_id: str 

@router.post("/threads/{thread_id}/messages", response_model=chat_schemas.ChatResponseSchema, tags=["Messages"])
async def send_message_and_get_rag_response(
    thread_id: str = Path(..., description="The ID of the thread to send the message to"),
    message_in: MessageCreateWithUserSchema = Body(...),
    db: Session = Depends(get_db)
):
    db_thread = crud.get_thread_by_id(db, thread_id=thread_id)
    if not db_thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    if db_thread.user_id != message_in.user_id:

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not authorized to post messages to this thread.")

    # 1. Save user's message
    crud.create_message_in_thread(db, thread_id=thread_id, role="user", content=message_in.content)

    # 2. Auto-update thread title
    if db_thread.title == "New Chat":
        current_messages_in_thread = crud.get_messages_for_thread(db, thread_id)
        if len(current_messages_in_thread) == 1 and current_messages_in_thread[0].role == "user":
            new_title = await generate_thead_title(message_in.content)
            if new_title:
                crud.update_thread(db, thread_id=thread_id, thread_update=models.ThreadUpdate(title=new_title))

    # 3. Prepare messages for LangGraph
    db_messages_models = crud.get_messages_for_thread(db, thread_id)
    langgraph_history: List[BaseMessage] = []
    for msg_model in db_messages_models:
        role = "human" if msg_model.role == "user" else "ai"
        message_constructor = HumanMessage if role == "human" else AIMessage
        langgraph_history.append(message_constructor(content=msg_model.content, id=str(msg_model.id)))
    
    initial_graph_state= {
        "user_id": message_in.user_id,
        "messages": langgraph_history,
        "retrieval_loop_count": 0
    }

    # 4. Invoke LangGraph
    try:
        final_graph_state = await compiled_rag_graph.ainvoke(initial_graph_state)
        ai_response_message = final_graph_state["messages"][-1]
        if not isinstance(ai_response_message, AIMessage):
            raise HTTPException(status_code=500, detail="RAG pipeline did not return an AI message.")
        assistant_content = ai_response_message.content
    except Exception as e:
        print(f"Error invoking RAG graph for thread {thread_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error generating AI response: {str(e)}")

    # 5. Save AI's message
    saved_assistant_message = crud.create_message_in_thread(db, thread_id=thread_id, role="assistant", content=assistant_content)

    return chat_schemas.ChatResponseSchema(
        assistant_message=assistant_content,
        thread_id=thread_id,
        new_message_id=saved_assistant_message.id
    )