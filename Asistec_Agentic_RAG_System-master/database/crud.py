from datetime import datetime, timezone
from typing import List, Optional
from sqlmodel import Session, select, delete
from sqlalchemy import desc
from . import models
from .models import FileProcessingStatusEnum

# --- User CRUD ---
def get_user_by_user_id(db: Session, user_id: str) -> Optional[models.User]:
    return db.get(models.User, user_id)

def create_user(db: Session, user_create_data: models.UserCreate) -> models.User: # Takes UserCreate model
    # Check if user_id already exists
    existing_user = db.get(models.User, user_create_data.user_id)
    if existing_user:
        raise ValueError(f"User with user_id '{user_create_data.user_id}' already exists.")

    # If email is provided, check for its uniqueness too if it's a constraint
    if user_create_data.email:
        user_with_email = db.exec(select(models.User).where(models.User.email == user_create_data.email)).first()
        if user_with_email:
            raise ValueError(f"Email '{user_create_data.email}' is already in use.")
            
    # Create a SQLModel User instance from the UserCreate Pydantic-like model
    db_user = models.User(
        user_id=user_create_data.user_id,
        email=user_create_data.email

    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Thread CRUD ---
def create_thread_for_user(db: Session, user_id: str, title: Optional[str] = "New Chat") -> models.Thread: # user_id is str
    db_thread = models.Thread(user_id=user_id, title=title or "New Chat")
    db.add(db_thread)
    db.commit()
    db.refresh(db_thread)
    return db_thread

def get_thread_by_id(db: Session, thread_id: str) -> Optional[models.Thread]:
    return db.get(models.Thread, thread_id) # Efficient PK lookup

def get_threads_for_user(db: Session, user_id: str) -> List[models.Thread]: # user_id is str
    statement = (
        select(models.Thread)
        .where(models.Thread.user_id == user_id)
        .order_by(desc(models.Thread.updated_at))
    )
    return db.exec(statement).all()

def update_thread(db: Session, thread_id: str, thread_update: models.ThreadUpdate) -> Optional[models.Thread]:
    db_thread = db.get(models.Thread, thread_id)
    if not db_thread:
        return None
    
    update_data = thread_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_thread, key, value)
    
    db_thread.updated_at = datetime.now(timezone.utc)
    db.add(db_thread)
    db.commit()
    db.refresh(db_thread)
    return db_thread

def delete_thread(db: Session, thread_id: str) -> bool:
    db_thread = db.get(models.Thread, thread_id)
    if not db_thread:
        return False
    db.delete(db_thread)
    db.commit()
    return True

# --- Message CRUD --- (No change needed here regarding user_id changes)
def create_message_in_thread(db: Session, thread_id: str, role: str, content: str) -> models.Message:
    db_thread = db.get(models.Thread, thread_id)
    if db_thread:
        db_thread.updated_at = datetime.now(timezone.utc)
        db.add(db_thread)
    
    db_message = models.Message(thread_id=thread_id, role=role, content=content)
    db.add(db_message)
    
    db.commit()
    if db_thread:
        db.refresh(db_thread)
    db.refresh(db_message)
    return db_message

def get_messages_for_thread(db: Session, thread_id: str) -> List[models.Message]:
    statement = (
        select(models.Message)
        .where(models.Message.thread_id == thread_id)
        .order_by(models.Message.timestamp.asc())
    )
    return db.exec(statement).all()


async def create_upload_job_in_db(db: Session, filenames: List[str]) -> models.UploadJob:
    job = models.UploadJob()
    db.add(job)
    db.commit() # Commit to get job.id
    db.refresh(job)

    for fname in filenames:
        file_attempt = models.FileProcessingAttempt(filename=fname, job_id=job.id)
        db.add(file_attempt)
    
    db.commit()
    db.refresh(job) # Refresh to get associated files
    return job

async def update_file_processing_status_in_db(
    db: Session,
    job_id: str,
    filename: str,
    status: FileProcessingStatusEnum,
    message: Optional[str] = None,
    chunks_indexed: Optional[int] = None,
):
    # Find the specific file attempt
    statement = select(models.FileProcessingAttempt).where(
        models.FileProcessingAttempt.job_id == job_id,
        models.FileProcessingAttempt.filename == filename
    )
    file_attempt = db.exec(statement).first()

    if file_attempt:
        file_attempt.status = status
        file_attempt.message = message
        if chunks_indexed is not None:
            file_attempt.chunks_indexed = chunks_indexed
        db.add(file_attempt)
    else:
        print(f"Warning: Could not find FileProcessingAttempt for job_id={job_id}, filename={filename} to update status.")
        return # Or raise error

    # Update the parent job's updated_at and overall_status
    job = db.get(models.UploadJob, job_id) # Use db.get for primary key lookup
    if job:
        job.updated_at = datetime.utcnow()
        
        # Recalculate overall job status
        # Need to fetch all files for this job again for accurate status
        all_files_for_job_stmt = select(models.FileProcessingAttempt).where(models.FileProcessingAttempt.job_id == job_id)
        all_files_status = db.exec(all_files_for_job_stmt).all()

        if not all_files_status: # Should not happen if job exists with files
            job.overall_status = FileProcessingStatusEnum.FAILED # Or some other error state
        elif all(f.status == FileProcessingStatusEnum.COMPLETED for f in all_files_status):
            job.overall_status = FileProcessingStatusEnum.COMPLETED
        elif any(f.status == FileProcessingStatusEnum.FAILED for f in all_files_status):
            # If any fail, and no PENDING/PROCESSING, then it's FAILED or PARTIAL
            # For simplicity, let's mark FAILED if any file fails and others are done.
             if not any(f.status in [FileProcessingStatusEnum.PENDING, FileProcessingStatusEnum.PROCESSING] for f in all_files_status):
                job.overall_status = FileProcessingStatusEnum.FAILED
             else: # Still some pending/processing
                job.overall_status = FileProcessingStatusEnum.PROCESSING
        elif any(f.status == FileProcessingStatusEnum.PROCESSING for f in all_files_status) or \
             any(f.status == FileProcessingStatusEnum.PENDING for f in all_files_status):
            job.overall_status = FileProcessingStatusEnum.PROCESSING
        else: # All are PENDING initially, will transition
            job.overall_status = FileProcessingStatusEnum.PENDING
            
        db.add(job)
    
    db.commit()
    if file_attempt: db.refresh(file_attempt)
    if job: db.refresh(job)

async def get_upload_job_from_db(db: Session, job_id: str) -> Optional[models.UploadJob]:

    return db.get(models.UploadJob, job_id)