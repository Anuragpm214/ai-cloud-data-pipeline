from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal

class RealtimeInferenceRequest(BaseModel):
    data_type: Literal["structured", "unstructured"] = Field(..., examples=["structured"]) # "structured" or "unstructured"
    features: Optional[List[float]] = Field(None, examples=[[1.2, 0.5, 3.4, 2.1]])
    text: Optional[str] = Field(None, examples=["High performance scalable cloud pipeline."])

class PredictionItem(BaseModel):
    id: str
    prediction_label: str
    confidence_score: float
    raw_output: List[float]

class RealtimeInferenceResponse(BaseModel):
    data_type: str
    prediction: PredictionItem

class BatchInferenceRequest(BaseModel):
    job_id: str
    s3_key: str
    data_type: Literal["structured", "unstructured"] = "structured"
    bucket: Optional[str] = None

class BatchInferenceResponse(BaseModel):
    job_id: str
    status: str
    total_samples: int
    predictions_count: int
    dynamodb_table: str
