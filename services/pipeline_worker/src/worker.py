import os
import time
import json
import boto3
import requests
from datetime import datetime, timezone
from . import config
from .validators.data_validator import DataValidator
from .transformers.structured import StructuredTransformer
from .transformers.unstructured import UnstructuredTransformer

def get_boto3_clients():
    session = boto3.Session(
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        region_name=config.AWS_REGION
    )
    s3 = session.client("s3", endpoint_url=config.AWS_ENDPOINT_URL or None)
    dynamodb = session.resource("dynamodb", endpoint_url=config.AWS_ENDPOINT_URL or None)
    sqs = session.client("sqs", endpoint_url=config.AWS_ENDPOINT_URL or None)
    return s3, dynamodb, sqs

def process_event(event_data: dict):
    s3, dynamodb, _ = get_boto3_clients()
    jobs_table = dynamodb.Table(config.DYNAMODB_JOB_TABLE)

    job_id = event_data["job_id"]
    bucket = event_data.get("bucket", config.S3_RAW_BUCKET)
    s3_key = event_data["s3_key"]
    data_type = event_data.get("data_type", "structured")
    filename = event_data.get("filename", "data.csv")

    print(f"[*] Processing Job {job_id} ({data_type}) from s3://{bucket}/{s3_key}")
    existing = jobs_table.get_item(Key={"job_id": job_id}, ConsistentRead=True).get("Item")
    if not existing:
        raise ValueError("Job must be registered before processing")
    if existing["status"] == "INFERENCE_COMPLETED":
        return
    now = datetime.now(timezone.utc).isoformat()

    # Update DynamoDB status to PROCESSING
    jobs_table.update_item(
        Key={"job_id": job_id},
        UpdateExpression="SET #st = :st, updated_at = :ua",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={":st": "PROCESSING", ":ua": now}
    )

    try:
        # 1. Download raw file from S3
        obj = s3.get_object(Bucket=bucket, Key=s3_key)
        raw_bytes = obj["Body"].read()

        # 2. Validate & Transform
        if data_type == "structured":
            is_valid, df, profile = DataValidator.validate_tabular_data(raw_bytes, filename)
            if not is_valid:
                raise ValueError(f"Validation failed: {profile.get('error')}")

            processed_bytes, transform_metrics = StructuredTransformer.transform(df)
            processed_key = f"processed/{job_id}/data.parquet"
            content_type = "application/octet-stream"
            record_count = transform_metrics["processed_rows"]
        elif data_type == "unstructured":
            is_valid, text_content, profile = DataValidator.validate_text_data(raw_bytes)
            if not is_valid:
                raise ValueError(f"Validation failed: {profile.get('error')}")

            processed_bytes, transform_metrics = UnstructuredTransformer.transform_text(text_content)
            processed_key = f"processed/{job_id}/data.json"
            content_type = "application/json"
            record_count = transform_metrics["chunks_count"]

        else:
            raise ValueError("Unsupported data_type")

        # 3. Store Transformed Data in S3
        s3.put_object(
            Bucket=config.S3_PROCESSED_BUCKET,
            Key=processed_key,
            Body=processed_bytes,
            ContentType=content_type
        )
        processed_s3_uri = f"s3://{config.S3_PROCESSED_BUCKET}/{processed_key}"

        now = datetime.now(timezone.utc).isoformat()
        metadata = {
            "validation_profile": profile,
            "transformation_metrics": transform_metrics
        }

        # 4. Update DynamoDB to TRANSFORMED
        jobs_table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #st = :st, processed_s3_uri = :puri, records_count = :rc, metadata = :meta, updated_at = :ua",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":st": "TRANSFORMED",
                ":puri": processed_s3_uri,
                ":rc": record_count,
                ":meta": metadata,
                ":ua": now
            }
        )
        print(f"[+] Job {job_id} successfully transformed and saved to {processed_s3_uri}")

        # 5. Trigger PyTorch AI Inference Service
        trigger_inference(job_id, processed_s3_uri, data_type, processed_key)

    except Exception as e:
        now = datetime.now(timezone.utc).isoformat()
        print(f"[-] Job {job_id} failed: {str(e)}")
        jobs_table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #st = :st, error_message = :err, updated_at = :ua",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":st": "FAILED",
                ":err": str(e),
                ":ua": now
            }
        )
        raise

def trigger_inference(job_id: str, processed_s3_uri: str, data_type: str, processed_key: str):
    response = requests.post(
        f"{config.AI_INFERENCE_URL}/api/v1/predict/batch",
        json={"job_id": job_id, "s3_key": processed_key,
              "data_type": data_type, "bucket": config.S3_PROCESSED_BUCKET},
        timeout=120,
    )
    response.raise_for_status()

def run_sqs_listener():
    print("[*] Pipeline Worker starting SQS queue polling...")
    _, _, sqs = get_boto3_clients()

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=config.SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                VisibilityTimeout=900,
                WaitTimeSeconds=10
            )
            messages = response.get("Messages", [])
            for msg in messages:
                receipt_handle = msg["ReceiptHandle"]
                body = json.loads(msg["Body"])
                process_event(body)

                # Delete processed message from queue
                sqs.delete_message(
                    QueueUrl=config.SQS_QUEUE_URL,
                    ReceiptHandle=receipt_handle
                )
        except Exception as e:
            print(f"Queue processing failed; message retained for retry: {e}")
            time.sleep(2)

if __name__ == "__main__":
    run_sqs_listener()
