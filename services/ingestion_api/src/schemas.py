from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum

class DataType(str, Enum):
    STRUCTURED = "structured"       # CSV, JSON, Parquet
    UNSTRUCTURED = "unstructured"   # UTF-8 text

class IngestionStatus(str, Enum):
    PENDING = "PENDING"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    TRANSFORMED = "TRANSFORMED"
    INFERENCE_COMPLETED = "INFERENCE_COMPLETED"
    FAILED = "FAILED"

class PresignedUrlRequest(BaseModel):
    filename: str = Field(..., examples=["dataset_2026.csv"])
    data_type: DataType = Field(default=DataType.STRUCTURED)
    content_type: Optional[str] = "text/csv"

class PresignedUrlResponse(BaseModel):
    job_id: str
    upload_url: str
    s3_key: str
    bucket: str
    expires_in: int

class DirectUploadResponse(BaseModel):
    job_id: str
    filename: str
    s3_key: str
    status: IngestionStatus
    message: str

class StoredPrediction(BaseModel):
    prediction_id: str
    job_id: str
    sample_index: int
    prediction_label: str
    confidence_score: float
    created_at: str
    chunk_preview: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: IngestionStatus
    filename: Optional[str] = None
    data_type: Optional[str] = None
    raw_s3_uri: Optional[str] = None
    processed_s3_uri: Optional[str] = None
    records_count: Optional[int] = None
    predictions_count: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    predictions: Optional[List[StoredPrediction]] = None
