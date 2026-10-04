import json
from services.pipeline_worker import lambda_function


def test_sqs_partial_failure(monkeypatch):
    processed = []
    def process(event):
        if event['job_id'] == 'bad':
            raise ValueError('bad record')
        processed.append(event)
    monkeypatch.setattr(lambda_function, 'process_event', process)
    result = lambda_function.lambda_handler({'Records': [
        {'messageId': '1', 'body': json.dumps({'job_id': 'bad'})},
        {'messageId': '2', 'body': json.dumps({'job_id': 'good'})},
    ]}, None)
    assert result == {'batchItemFailures': [{'itemIdentifier': '1'}]}
    assert processed == [{'job_id': 'good'}]


def test_nested_s3_event(monkeypatch):
    processed = []
    monkeypatch.setattr(lambda_function, 'process_event', processed.append)
    event = {'Records': [{'s3': {'bucket': {'name': 'raw'}, 'object': {'key': 'structured/job_file+name.csv'}}}]}
    result = lambda_function.lambda_handler({'Records': [{'messageId': '1', 'body': json.dumps(event)}]}, None)
    assert result == {'batchItemFailures': []}
    assert processed[0]['filename'] == 'file name.csv'
    assert processed[0]['job_id'] == 'job'
