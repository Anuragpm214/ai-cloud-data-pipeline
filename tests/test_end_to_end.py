import pytest
import os
import sys
import boto3
from moto import mock_aws

# Add service paths

@pytest.fixture
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_ENDPOINT_URL"] = ""

@mock_aws
def test_full_pipeline_flow(aws_credentials):
    # Setup AWS mocked resources
    s3 = boto3.client("s3", region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    sqs = boto3.client("sqs", region_name="us-east-1")

    raw_bucket = "raw-data-bucket"
    processed_bucket = "processed-data-bucket"
    s3.create_bucket(Bucket=raw_bucket)
    s3.create_bucket(Bucket=processed_bucket)

    # Create DynamoDB tables
    jobs_table = dynamodb.create_table(
        TableName="PipelineJobs",
        KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST"
    )

    pred_table = dynamodb.create_table(
        TableName="ModelPredictions",
        KeySchema=[{"AttributeName": "prediction_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "prediction_id", "AttributeType": "S"},
            {"AttributeName": "job_id", "AttributeType": "S"}
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "JobIdIndex",
                "KeySchema": [{"AttributeName": "job_id", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"}
            }
        ],
        BillingMode="PAY_PER_REQUEST"
    )

    # 1. Ingestion: Upload raw structured CSV
    job_id = "test-job-123"
    s3_key = f"structured/{job_id}_sample.csv"
    csv_bytes = b"feature1,feature2,feature3,feature4\n1.2,0.5,3.1,2.0\n4.5,1.1,0.2,3.3\n"

    s3.put_object(Bucket=raw_bucket, Key=s3_key, Body=csv_bytes)
    jobs_table.put_item(Item={
        "job_id": job_id,
        "filename": "sample.csv",
        "data_type": "structured",
        "s3_key": s3_key,
        "status": "UPLOADED"
    })

    # 2. Worker Transformation
    from services.pipeline_worker.src.validators.data_validator import DataValidator
    from services.pipeline_worker.src.transformers.structured import StructuredTransformer

    is_valid, df, profile = DataValidator.validate_tabular_data(csv_bytes, "sample.csv")
    assert is_valid is True
    parquet_bytes, metrics = StructuredTransformer.transform(df)

    proc_key = f"processed/{job_id}/data.parquet"
    s3.put_object(Bucket=processed_bucket, Key=proc_key, Body=parquet_bytes)

    # 3. PyTorch Inference
    from services.ai_inference.src.pipelines.inference_engine import InferenceEngine
    engine = InferenceEngine()
    # Mock engine's boto3 clients with mocked session
    engine._get_boto3_clients = lambda: (s3, dynamodb)

    count = engine.process_batch(
        job_id=job_id,
        s3_key=proc_key,
        data_type="structured",
        bucket=processed_bucket
    )
    assert count == 2

    # 4. Verify Final State in DynamoDB
    final_job = jobs_table.get_item(Key={"job_id": job_id}).get("Item")
    assert final_job["status"] == "INFERENCE_COMPLETED"
    assert final_job["predictions_count"] == 2

    preds = pred_table.query(
        IndexName="JobIdIndex",
        KeyConditionExpression="job_id = :jid",
        ExpressionAttributeValues={":jid": job_id}
    ).get("Items", [])
    assert len(preds) == 2
    assert "prediction_label" in preds[0]
    assert "confidence_score" in preds[0]
