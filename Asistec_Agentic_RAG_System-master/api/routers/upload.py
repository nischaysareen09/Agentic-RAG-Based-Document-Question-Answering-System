# RAG_Chatbot/api/routers/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException, status, BackgroundTasks, Path, Depends
from typing import List, Optional
from sqlmodel import Session

from api.schemas.documents import UploadFileResponse, JobStatusResponse
from core.docs_processing import process_and_index_pdf
from database.database import get_db
from database import crud as db_crud 
from database.models import FileProcessingStatusEnum

router = APIRouter()

async def _index_file_in_background_db(
    job_id: str,
    file_bytes: bytes, 
    filename: str,
):
    """
    Internal helper function to run the indexing process in a background task.
    Updates the status in the database.
    """
    # Important: Each background task needs its own DB session
    db: Session = next(get_db())
    try:
        print(f"Background task started for: job_id={job_id}, filename={filename}")
        await db_crud.update_file_processing_status_in_db(
            db, job_id, filename, FileProcessingStatusEnum.PROCESSING
        )
        
        num_chunks_indexed = await process_and_index_pdf(file_bytes, filename, custom_metadata=None) # No custom_metadata from user
        
        await db_crud.update_file_processing_status_in_db(
            db, 
            job_id, 
            filename, 
            FileProcessingStatusEnum.COMPLETED,
            message=f"Successfully indexed with {num_chunks_indexed} chunks.",
            chunks_indexed=num_chunks_indexed
        )
        print(f"Background task: Successfully indexed {filename} (job: {job_id}) with {num_chunks_indexed} chunks.")
    except Exception as e:
        error_message = f"Error indexing {filename}: {str(e)}"
        print(f"Background task: {error_message} (job: {job_id})")
        await db_crud.update_file_processing_status_in_db(
            db, 
            job_id, 
            filename, 
            FileProcessingStatusEnum.FAILED,
            message=error_message
        )
    finally:
        db.close()


@router.post(
    "/upload", 
    response_model=UploadFileResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload PDF files for asynchronous indexing (Internal Use)",
    description=(
        "Accepts one or more PDF files. Processing and indexing are performed in the background. "
        "Returns a `job_id` that can be used to check the status of the processing. "
        "This endpoint is intended for internal use and does not accept user-defined tags."
    )
)
async def upload_pdf_files_for_indexing_internal( # Renamed for clarity
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), # Inject DB session for main thread operations
    files: List[UploadFile] = File(..., description="One or more PDF files to upload.")
):
    files_to_schedule_names = []
    files_rejected_names = []
    
    valid_files_for_job: List[dict] = []
    for file_idx, file in enumerate(files):
        original_filename = file.filename or f"unnamed_pdf_{file_idx}"
        if file.content_type != "application/pdf":
            files_rejected_names.append(original_filename)
            continue
        
        try:
            file_bytes = await file.read() 
            valid_files_for_job.append({
                "filename": original_filename,
                "bytes": file_bytes
            })
            files_to_schedule_names.append(original_filename)
        except Exception as e:
            print(f"Error preparing file {original_filename} for upload: {e}")
            files_rejected_names.append(original_filename)
            
    if not valid_files_for_job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid PDF files provided or files could not be read.",
            headers={"X-Files-Rejected": ",".join(files_rejected_names)} if files_rejected_names else None
        )

    # Create a job ID for this upload batch using the DB
    job_db = await db_crud.create_upload_job_in_db(db, [f_info["filename"] for f_info in valid_files_for_job])
    job_id = job_db.id

    # Schedule background tasks for valid files
    for file_info in valid_files_for_job:
        background_tasks.add_task(
            _index_file_in_background_db, 
            job_id,
            file_info["bytes"],
            file_info["filename"],
        )
        print(f"Scheduled {file_info['filename']} for background indexing (Job ID: {job_id}).")
    
    message = f"Processing job {job_id} scheduled for {len(valid_files_for_job)} file(s)."
    if files_rejected_names:
        message += f" {len(files_rejected_names)} file(s) were rejected."

    return UploadFileResponse(
        job_id=job_id,
        status="accepted",
        message=message,
        files_scheduled=files_to_schedule_names,
        files_rejected=files_rejected_names
    )

@router.get(
    "/upload/status/{job_id}",
    response_model=JobStatusResponse,
    summary="Get the processing status of an upload job (Internal Use)",
    description="Poll this endpoint with the `job_id` received from the `/upload` endpoint to track file indexing progress."
)
async def get_upload_job_status_internal( 
    job_id: str = Path(..., description="The ID of the upload job to check."),
    db: Session = Depends(get_db)
):
    job_status_db = await db_crud.get_upload_job_from_db(db, job_id)
    if not job_status_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job ID {job_id} not found.")

    return JobStatusResponse.from_orm(job_status_db)