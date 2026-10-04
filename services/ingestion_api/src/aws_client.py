import boto3
from .config import settings

def get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL or None,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

def get_dynamodb_resource():
    return boto3.resource(
        "dynamodb",
        region_name=settings.AWS_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL or None,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

def get_sqs_client():
    return boto3.client(
        "sqs",
        region_name=settings.AWS_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL or None,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
