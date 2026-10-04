"""Lambda adapter; enable ReportBatchItemFailures for the SQS event source."""
import json
import urllib.parse

if __package__:
    from .src.worker import process_event
else:
    from src.worker import process_event


def dispatch(event):
    if 'Records' not in event:
        if event.get('Event') == 's3:TestEvent':
            return
        process_event(event)
        return
    for record in event['Records']:
        if 's3' in record:
            bucket = record['s3']['bucket']['name']
            key = urllib.parse.unquote_plus(record['s3']['object']['key'])
            data_type, name = key.split('/', 1)
            job_id, filename = name.split('_', 1)
            process_event(dict(job_id=job_id, bucket=bucket, s3_key=key,
                               data_type=data_type, filename=filename))
        elif 'body' in record:
            dispatch(json.loads(record['body']))
        else:
            raise ValueError('Unsupported event record')


def lambda_handler(event, context):
    failures = []
    for record in event.get('Records', []):
        if 'body' in record:
            try:
                dispatch(json.loads(record['body']))
            except Exception:
                failures.append({'itemIdentifier': record['messageId']})
        else:
            dispatch({'Records': [record]})
    if 'Records' not in event:
        dispatch(event)
    return {'batchItemFailures': failures}
