#!/bin/bash
set -e

echo "=== Initializing LocalStack AWS Resources ==="

export AWS_DEFAULT_REGION=us-east-1

# 1. Create S3 Buckets
echo "Creating S3 buckets..."
awslocal s3api head-bucket --bucket raw-data-bucket 2>/dev/null || awslocal s3 mb s3://raw-data-bucket
awslocal s3api head-bucket --bucket processed-data-bucket 2>/dev/null || awslocal s3 mb s3://processed-data-bucket

# 2. Create DynamoDB Tables
echo "Creating DynamoDB PipelineJobs table..."
awslocal dynamodb describe-table --table-name PipelineJobs 2>/dev/null || awslocal dynamodb create-table \
    --table-name PipelineJobs \
    --attribute-definitions \
        AttributeName=job_id,AttributeType=S \
        AttributeName=created_at,AttributeType=S \
    --key-schema \
        AttributeName=job_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --global-secondary-indexes \
        "[{\"IndexName\": \"CreatedAtIndex\", \"KeySchema\": [{\"AttributeName\":\"created_at\",\"KeyType\":\"HASH\"}], \"Projection\":{\"ProjectionType\":\"ALL\"}}]"

echo "Creating DynamoDB ModelPredictions table..."
awslocal dynamodb describe-table --table-name ModelPredictions 2>/dev/null || awslocal dynamodb create-table \
    --table-name ModelPredictions \
    --attribute-definitions \
        AttributeName=prediction_id,AttributeType=S \
        AttributeName=job_id,AttributeType=S \
    --key-schema \
        AttributeName=prediction_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --global-secondary-indexes \
        "[{\"IndexName\": \"JobIdIndex\", \"KeySchema\": [{\"AttributeName\":\"job_id\",\"KeyType\":\"HASH\"}], \"Projection\":{\"ProjectionType\":\"ALL\"}}]"

# 3. Create SQS Queue for Asynchronous Event Processing
echo "Creating SQS Queue for data processing..."
awslocal sqs create-queue --queue-name data-processing-dlq
awslocal sqs create-queue --queue-name data-processing-queue --attributes '{"VisibilityTimeout":"900","RedrivePolicy":"{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:000000000000:data-processing-dlq\",\"maxReceiveCount\":\"5\"}"}'

echo "=== AWS Resources Successfully Initialized ==="
