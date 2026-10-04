import json
import boto3
import pytest
import requests
from fastapi.testclient import TestClient
from moto import mock_aws


@pytest.fixture
def pipeline(monkeypatch):
    with mock_aws():
        from services.ingestion_api.src.api import routes
        from services.ingestion_api.src.main import app
        from services.pipeline_worker.src import worker
        from services.ai_inference.src.pipelines.inference_engine import inference_engine
        s3 = boto3.client('s3', region_name='us-east-1')
        db = boto3.resource('dynamodb', region_name='us-east-1')
        sqs = boto3.client('sqs', region_name='us-east-1')
        for bucket in ['raw-data-bucket', 'processed-data-bucket']:
            s3.create_bucket(Bucket=bucket)
        jobs = db.create_table(TableName='PipelineJobs', KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}], AttributeDefinitions=[{'AttributeName': 'job_id', 'AttributeType': 'S'}], BillingMode='PAY_PER_REQUEST')
        preds = db.create_table(TableName='ModelPredictions', KeySchema=[{'AttributeName': 'prediction_id', 'KeyType': 'HASH'}], AttributeDefinitions=[{'AttributeName': 'prediction_id', 'AttributeType': 'S'}, {'AttributeName': 'job_id', 'AttributeType': 'S'}], GlobalSecondaryIndexes=[{'IndexName': 'JobIdIndex', 'KeySchema': [{'AttributeName': 'job_id', 'KeyType': 'HASH'}], 'Projection': {'ProjectionType': 'ALL'}}], BillingMode='PAY_PER_REQUEST')
        queue = sqs.create_queue(QueueName='pipeline')['QueueUrl']
        monkeypatch.setattr(routes.s3_service, 's3_client', s3)
        monkeypatch.setattr(routes.s3_service, 'sqs_client', sqs)
        monkeypatch.setattr(routes.settings, 'SQS_QUEUE_URL', queue)
        monkeypatch.setattr(routes.job_service, 'jobs_table', jobs)
        monkeypatch.setattr(routes.job_service, 'predictions_table', preds)
        monkeypatch.setattr(worker, 'get_boto3_clients', lambda: (s3, db, sqs))
        monkeypatch.setattr(inference_engine, '_get_boto3_clients', lambda: (s3, db))
        def infer(job_id, uri, data_type, key):
            inference_engine.process_batch(job_id, key, data_type)
        monkeypatch.setattr(worker, 'trigger_inference', infer)
        yield TestClient(app), s3, sqs, queue, worker, routes


@pytest.mark.parametrize('filename,content,data_type,count', [
    ('data.csv', b'a,b,c,d\n1,2,3,4\n5,6,7,8\n', 'structured', 2),
    ('data.txt', b'Hello world. Another sentence!', 'unstructured', 2),
    ('data.JSON', b'[{"a":1,"b":2,"c":3,"d":4}]', 'structured', 1),
])
def test_upload_worker_inference(pipeline, filename, content, data_type, count):
    client, s3, sqs, queue, worker, routes = pipeline
    response = client.post('/api/v1/upload', files={'file': (filename, content)}, data={'data_type': data_type})
    assert response.status_code == 200, response.text
    job_id = response.json()['job_id']
    event = json.loads(sqs.receive_message(QueueUrl=queue)['Messages'][0]['Body'])
    assert routes.job_service.get_job(job_id)['status'] == 'UPLOADED'
    worker.process_event(event)
    worker.process_event(event)  # redelivery does not create more predictions
    result = client.get(f'/api/v1/jobs/{job_id}').json()
    assert result['status'] == 'INFERENCE_COMPLETED'
    assert result['records_count'] == count
    assert len(result['predictions']) == count
    assert isinstance(result['predictions'][0]['confidence_score'], (float, int))


def test_presigned_completion(pipeline):
    client, s3, sqs, queue, worker, routes = pipeline
    response = client.post('/api/v1/presigned-url', json={'filename': 'data.txt', 'data_type': 'unstructured'})
    assert response.status_code == 200
    job = response.json()
    path = f"/api/v1/jobs/{job['job_id']}"
    assert client.get(path).json()['status'] == 'PENDING'
    assert client.post(path + '/complete-upload').status_code == 409
    s3.put_object(Bucket=job['bucket'], Key=job['s3_key'], Body=b'Hello world.')
    assert client.post(path + '/complete-upload').status_code == 200
    assert client.post(path + '/complete-upload').status_code == 200
    messages = sqs.receive_message(QueueUrl=queue, MaxNumberOfMessages=10)['Messages']
    assert len(messages) == 1
    worker.process_event(json.loads(messages[0]['Body']))
    assert client.get(path).json()['status'] == 'INFERENCE_COMPLETED'


def test_worker_failure_is_retryable(pipeline, monkeypatch):
    client, s3, sqs, queue, worker, routes = pipeline
    response = client.post('/api/v1/upload', files={'file': ('data.txt', b'hello')}, data={'data_type': 'unstructured'})
    event = json.loads(sqs.receive_message(QueueUrl=queue)['Messages'][0]['Body'])
    def fail(*args):
        raise requests.ConnectionError('inference unavailable')
    monkeypatch.setattr(worker, 'trigger_inference', fail)
    with pytest.raises(requests.ConnectionError):
        worker.process_event(event)
    assert routes.job_service.get_job(response.json()['job_id'])['status'] == 'FAILED'


def test_reject_invalid_uploads(pipeline):
    client, *_ = pipeline
    for filename, content in [('empty.csv', b''), ('bad.exe', b'123'), ('../file.csv', b'123')]:
        assert client.post('/api/v1/upload', files={'file': (filename, content)}).status_code == 400
    assert client.get('/api/v1/jobs/missing').status_code == 404


def test_inference_bad_inputs():
    from services.ai_inference.src.main import app
    client = TestClient(app)
    for payload in [{'data_type': 'structured'}, {'data_type': 'structured', 'features': [1]}, {'data_type': 'unstructured', 'text': ''}]:
        assert client.post('/api/v1/predict/realtime', json=payload).status_code == 400
    assert client.post('/api/v1/predict/realtime', json={'data_type': 'other'}).status_code == 422
    assert client.get('/health').json()['model_mode'] == 'untrained_demo'


def test_queue_failure_is_visible(pipeline, monkeypatch):
    client, s3, sqs, queue, worker, routes = pipeline
    def fail(*args, **kwargs):
        raise RuntimeError('queue unavailable')
    monkeypatch.setattr(routes.s3_service, 'send_processing_event', fail)
    response = client.post('/api/v1/upload', files={'file': ('data.csv', b'a,b,c,d\n1,2,3,4')})
    assert response.status_code == 500
    jobs = routes.job_service.jobs_table.scan()['Items']
    assert jobs[0]['status'] == 'FAILED'


def test_inference_http_failure_propagates(monkeypatch):
    from services.pipeline_worker import src
    from services.pipeline_worker.src import worker
    response = requests.Response()
    response.status_code = 503
    monkeypatch.setattr(worker.requests, 'post', lambda *args, **kwargs: response)
    with pytest.raises(requests.HTTPError):
        worker.trigger_inference('job', 's3://bucket/key', 'structured', 'key')
