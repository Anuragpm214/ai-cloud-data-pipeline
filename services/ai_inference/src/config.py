import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ENDPOINT_URL: str | None = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "test")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "test")

    S3_PROCESSED_BUCKET: str = os.getenv("S3_PROCESSED_BUCKET", "processed-data-bucket")
    DYNAMODB_JOB_TABLE: str = os.getenv("DYNAMODB_JOB_TABLE", "PipelineJobs")
    DYNAMODB_PREDICTIONS_TABLE: str = os.getenv("DYNAMODB_PREDICTIONS_TABLE", "ModelPredictions")

settings = Settings()
