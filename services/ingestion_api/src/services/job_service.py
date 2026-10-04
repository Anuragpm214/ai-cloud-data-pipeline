from datetime import datetime, timezone
from typing import Optional, Dict, Any
from ..aws_client import get_dynamodb_resource
from ..config import settings
from ..schemas import IngestionStatus

class JobService:
    def __init__(self):
        self.dynamodb = get_dynamodb_resource()
        self.jobs_table = self.dynamodb.Table(settings.DYNAMODB_JOB_TABLE)
        self.predictions_table = self.dynamodb.Table(settings.DYNAMODB_PREDICTIONS_TABLE)

    def create_job(self, job_id: str, filename: str, data_type: str, s3_key: str, status: IngestionStatus = IngestionStatus.UPLOADED) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "job_id": job_id,
            "filename": filename,
            "data_type": data_type,
            "raw_s3_uri": f"s3://{settings.S3_RAW_BUCKET}/{s3_key}",
            "s3_key": s3_key,
            "status": status.value,
            "created_at": now,
            "updated_at": now,
            "metadata": {}
        }
        self.jobs_table.put_item(Item=item)
        return item

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        response = self.jobs_table.get_item(Key={"job_id": job_id}, ConsistentRead=True)
        item = response.get("Item")
        if not item:
            return None

        query = dict(IndexName="JobIdIndex", KeyConditionExpression="job_id = :jid",
                     ExpressionAttributeValues={":jid": job_id})
        item["predictions"] = []
        while True:
            response = self.predictions_table.query(**query)
            item["predictions"].extend(response.get("Items", []))
            if "LastEvaluatedKey" not in response:
                break
            query["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        item["predictions"].sort(key=lambda prediction: prediction["sample_index"])

        return item

    def update_job_status(self, job_id: str, status: IngestionStatus, **kwargs):
        now = datetime.now(timezone.utc).isoformat()
        update_expr = "SET #st = :st, updated_at = :ua"
        expr_names = {"#st": "status"}
        expr_values = {":st": status.value, ":ua": now}

        for k, v in kwargs.items():
            if v is not None:
                update_expr += f", {k} = :{k}"
                expr_values[f":{k}"] = v

        self.jobs_table.update_item(
            Key={"job_id": job_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values
        )
