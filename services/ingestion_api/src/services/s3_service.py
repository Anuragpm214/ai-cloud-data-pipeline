import uuid
import json
from ..aws_client import get_s3_client, get_sqs_client
from ..config import settings

class S3Service:
    def __init__(self):
        self.s3_client = get_s3_client()
        self.sqs_client = get_sqs_client()

    def generate_presigned_url(self, filename: str, data_type: str, content_type: str = "application/octet-stream", expires_in: int = 3600):
        job_id = str(uuid.uuid4())
        s3_key = f"{data_type}/{job_id}_{filename}"

        signing_client = self.s3_client
        if settings.S3_PUBLIC_ENDPOINT_URL:
            import boto3
            from botocore.config import Config
            signing_client = boto3.client(
                "s3", endpoint_url=settings.S3_PUBLIC_ENDPOINT_URL,
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            )
        url = signing_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.S3_RAW_BUCKET,
                "Key": s3_key,
                "ContentType": content_type
            },
            ExpiresIn=expires_in
        )
        return job_id, s3_key, url

    def upload_file_bytes(self, file_bytes: bytes, filename: str, data_type: str) -> tuple[str, str]:
        job_id = str(uuid.uuid4())
        s3_key = f"{data_type}/{job_id}_{filename}"

        self.s3_client.put_object(
            Bucket=settings.S3_RAW_BUCKET,
            Key=s3_key,
            Body=file_bytes
        )

        return job_id, s3_key

    def send_processing_event(self, job_id: str, s3_key: str, data_type: str, filename: str):
        message_body = {
            "job_id": job_id,
            "bucket": settings.S3_RAW_BUCKET,
            "s3_key": s3_key,
            "data_type": data_type,
            "filename": filename
        }
        self.sqs_client.send_message(
            QueueUrl=settings.SQS_QUEUE_URL,
            MessageBody=json.dumps(message_body)
        )
