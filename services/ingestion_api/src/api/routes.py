from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Optional
from ..schemas import (
    PresignedUrlRequest,
    PresignedUrlResponse,
    DirectUploadResponse,
    JobStatusResponse,
    DataType,
    IngestionStatus
)
from ..services.s3_service import S3Service
from ..services.job_service import JobService
from ..config import settings

router = APIRouter()
s3_service = S3Service()
job_service = JobService()

@router.post("/upload", response_model=DirectUploadResponse)
async def direct_upload(
    file: UploadFile = File(...),
    data_type: DataType = Form(default=DataType.STRUCTURED)
):
    """Directly ingest structured (CSV/JSON/Parquet) or unstructured (UTF-8 text) datasets."""
    try:
        content = await file.read(settings.MAX_UPLOAD_BYTES + 1)
        if not content:
            raise HTTPException(status_code=400, detail="File is empty")
        if len(content) > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File exceeds upload limit")
        validate_filename(file.filename, data_type)
        job_id, s3_key = s3_service.upload_file_bytes(
            file_bytes=content,
            filename=file.filename,
            data_type=data_type.value
        )

        job_service.create_job(
            job_id=job_id,
            filename=file.filename,
            data_type=data_type.value,
            s3_key=s3_key
        )

        try:
            s3_service.send_processing_event(job_id, s3_key, data_type.value, file.filename)
        except Exception as exc:
            job_service.update_job_status(job_id, IngestionStatus.FAILED, error_message=str(exc))
            raise
        return DirectUploadResponse(
            job_id=job_id,
            filename=file.filename,
            s3_key=s3_key,
            status=IngestionStatus.UPLOADED,
            message="File uploaded successfully and scheduled for processing."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/presigned-url", response_model=PresignedUrlResponse)
async def get_presigned_url(request: PresignedUrlRequest):
    """Generate presigned S3 URL for large dataset uploads."""
    try:
        validate_filename(request.filename, request.data_type)
        job_id, s3_key, url = s3_service.generate_presigned_url(
            filename=request.filename,
            data_type=request.data_type.value,
            content_type=request.content_type or "application/octet-stream"
        )

        job_service.create_job(
            job_id=job_id,
            filename=request.filename,
            data_type=request.data_type.value,
            s3_key=s3_key,
            status=IngestionStatus.PENDING
        )

        return PresignedUrlResponse(
            job_id=job_id,
            upload_url=url,
            s3_key=s3_key,
            bucket=settings.S3_RAW_BUCKET,
            expires_in=3600
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL: {str(e)}")

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Query ingestion, transformation, and AI inference status by Job ID."""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return job


def validate_filename(filename: str, data_type: DataType):
    from pathlib import PurePosixPath
    allowed = {DataType.STRUCTURED: {".csv", ".json", ".parquet"},
               DataType.UNSTRUCTURED: {".txt"}}
    if not filename or "/" in filename or "\\" in filename or PurePosixPath(filename).suffix.lower() not in allowed[data_type]:
        raise HTTPException(status_code=400, detail="Use a CSV, JSON or Parquet filename for structured data, or TXT for text")


@router.post("/jobs/{job_id}/complete-upload", response_model=JobStatusResponse)
def complete_upload(job_id: str):
    """Confirm a presigned PUT and enqueue its registered job. Safe to repeat after success."""
    from botocore.exceptions import ClientError
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != IngestionStatus.PENDING:
        return job
    try:
        obj = s3_service.s3_client.head_object(Bucket=settings.S3_RAW_BUCKET, Key=job["s3_key"])
    except ClientError as exc:
        if exc.response["Error"]["Code"] in {"404", "NoSuchKey", "NotFound"}:
            raise HTTPException(status_code=409, detail="Upload the file before completing the job") from exc
        raise
    if not obj["ContentLength"]:
        raise HTTPException(status_code=400, detail="File is empty")
    # Register the state before publishing so the worker cannot be overwritten.
    job_service.update_job_status(job_id, IngestionStatus.UPLOADED)
    try:
        s3_service.send_processing_event(job_id, job["s3_key"], job["data_type"], job["filename"])
    except Exception as exc:
        job_service.update_job_status(job_id, IngestionStatus.PENDING)
        raise HTTPException(status_code=503, detail="Scheduling failed; retry completion") from exc
    return job_service.get_job(job_id)
