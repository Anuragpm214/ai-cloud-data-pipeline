from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import (
    RealtimeInferenceRequest,
    RealtimeInferenceResponse,
    PredictionItem,
    BatchInferenceRequest,
    BatchInferenceResponse
)
from .pipelines.inference_engine import inference_engine
from .config import settings

app = FastAPI(
    title="PyTorch AI Inference Service",
    description="High-performance real-time and batch deep learning inference engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "ai-inference", "device": str(inference_engine.device), "model_mode": "untrained_demo"}

@app.post("/api/v1/predict/realtime", response_model=RealtimeInferenceResponse)
def realtime_predict(request: RealtimeInferenceRequest):
    """Run real-time PyTorch inference on individual data instances."""
    try:
        if request.data_type == "structured":
            if request.features is None:
                raise HTTPException(status_code=400, detail="`features` list required for structured prediction.")
            result = inference_engine.predict_tabular_single(request.features)
        elif request.data_type == "unstructured":
            if not request.text:
                raise HTTPException(status_code=400, detail="`text` string required for unstructured prediction.")
            result = inference_engine.predict_text_single(request.text)
        else:
            raise HTTPException(status_code=400, detail="Unsupported data_type. Use 'structured' or 'unstructured'.")

        return RealtimeInferenceResponse(
            data_type=request.data_type,
            prediction=PredictionItem(**result)
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@app.post("/api/v1/predict/batch", response_model=BatchInferenceResponse)
def batch_predict(request: BatchInferenceRequest):
    """Run batch PyTorch inference on S3 processed datasets and write results to DynamoDB."""
    try:
        count = inference_engine.process_batch(
            job_id=request.job_id,
            s3_key=request.s3_key,
            data_type=request.data_type,
            bucket=request.bucket
        )
        return BatchInferenceResponse(
            job_id=request.job_id,
            status="SUCCESS",
            total_samples=count,
            predictions_count=count,
            dynamodb_table=settings.DYNAMODB_PREDICTIONS_TABLE
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch inference error: {str(e)}")
