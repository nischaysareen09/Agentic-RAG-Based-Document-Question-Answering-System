from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from database.database import engine
from database.models import create_db_and_tables
from api.routers import chat, memory, upload

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"INFO:     Starting up {settings.APP_NAME} v{settings.APP_VERSION}...")
    create_db_and_tables(engine)
    print("INFO:     Database tables checked/created.")
    yield
    print(f"INFO:     Shutting down {settings.APP_NAME}...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Advanced Agentic RAG backend system to chat with company documents.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": f"{settings.APP_NAME} is running!"}

# Include API routers with a common prefix
app.include_router(chat.router, prefix="/api")
app.include_router(memory.router, prefix="/api", tags=["Memories"])
app.include_router(upload.router, prefix="/api", tags=["Document Management (Internal)"]) # Updated tag

