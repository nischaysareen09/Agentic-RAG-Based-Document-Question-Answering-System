from sqlmodel import create_engine, Session
from core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=settings.DB_CONNECT_ARGS,
    pool_size=20, 
    max_overflow=10,
)

def get_db():
    with Session(engine) as session:
        yield session