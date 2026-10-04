import os

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "test")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "test")

S3_RAW_BUCKET = os.getenv("S3_RAW_BUCKET", "raw-data-bucket")
S3_PROCESSED_BUCKET = os.getenv("S3_PROCESSED_BUCKET", "processed-data-bucket")
DYNAMODB_JOB_TABLE = os.getenv("DYNAMODB_JOB_TABLE", "PipelineJobs")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "http://localhost:4566/000000000000/data-processing-queue")
AI_INFERENCE_URL = os.getenv("AI_INFERENCE_URL", "http://localhost:8001")
