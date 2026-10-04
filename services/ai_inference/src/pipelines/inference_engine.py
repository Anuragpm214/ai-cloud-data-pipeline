import io
import json
import uuid
import hashlib
from decimal import Decimal
import boto3
import torch
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from ..config import settings
from ..models.pytorch_models import TabularClassifier, TextEmbeddingClassifier

class InferenceEngine:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[*] Initializing InferenceEngine on device: {self.device}")

        torch.manual_seed(42)
        # Deterministic demo weights; these models are not trained.
        # Initialize Models with evaluation mode
        self.tabular_model = TabularClassifier(input_dim=4, num_classes=2).to(self.device)
        self.tabular_model.eval()

        self.text_model = TextEmbeddingClassifier(vocab_size=5000, embed_dim=64, num_classes=3).to(self.device)
        self.text_model.eval()

        self.text_labels = ["NEGATIVE", "NEUTRAL", "POSITIVE"]
        self.tabular_labels = ["LOW_RISK", "HIGH_RISK"]

    def _get_boto3_clients(self):
        session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        s3 = session.client("s3", endpoint_url=settings.AWS_ENDPOINT_URL or None)
        dynamodb = session.resource("dynamodb", endpoint_url=settings.AWS_ENDPOINT_URL or None)
        return s3, dynamodb

    def predict_tabular_single(self, features: list[float]) -> dict:
        """Run real-time inference on a feature vector."""
        if len(features) != 4 or not np.isfinite(features).all():
            raise ValueError("Exactly four finite numeric features are required")

        x = torch.tensor([features], dtype=torch.float32).to(self.device)
        with torch.no_grad():
            logits = self.tabular_model(x)
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
            pred_class = int(np.argmax(probs))

        return {
            "id": str(uuid.uuid4()),
            "prediction_label": self.tabular_labels[pred_class],
            "confidence_score": float(probs[pred_class]),
            "raw_output": [float(p) for p in probs]
        }

    def predict_text_single(self, text: str) -> dict:
        """Run real-time text inference."""
        tokens = [int.from_bytes(hashlib.sha256(w.lower().encode()).digest()[:8], "big") % 5000 for w in text.split()]
        if not tokens:
            tokens = [0]

        text_tensor = torch.tensor(tokens, dtype=torch.long).to(self.device)
        offsets = torch.tensor([0], dtype=torch.long).to(self.device)

        with torch.no_grad():
            logits = self.text_model(text_tensor, offsets)
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
            pred_class = int(np.argmax(probs))

        return {
            "id": str(uuid.uuid4()),
            "prediction_label": self.text_labels[pred_class],
            "confidence_score": float(probs[pred_class]),
            "raw_output": [float(p) for p in probs]
        }

    def process_batch(self, job_id: str, s3_key: str, data_type: str, bucket: str = None) -> int:
        """Fetch processed data from S3, run batch PyTorch inference, and save predictions to DynamoDB."""
        bucket = bucket or settings.S3_PROCESSED_BUCKET
        s3, dynamodb = self._get_boto3_clients()
        pred_table = dynamodb.Table(settings.DYNAMODB_PREDICTIONS_TABLE)
        jobs_table = dynamodb.Table(settings.DYNAMODB_JOB_TABLE)

        # 1. Download processed file from S3
        obj = s3.get_object(Bucket=bucket, Key=s3_key)
        content_bytes = obj["Body"].read()

        predictions = []
        now = datetime.now(timezone.utc).isoformat()

        if data_type == "structured":
            df = pd.read_parquet(io.BytesIO(content_bytes))
            # Pick numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) != 4:
                raise ValueError("Structured inference requires exactly four numeric columns")
            for idx, (_, row) in enumerate(df.iterrows()):
                vals = [float(row[c]) for c in numeric_cols]
                pred = self.predict_tabular_single(vals)
                pred_item = {
                    "prediction_id": f"{job_id}_{idx}",
                    "job_id": job_id,
                    "sample_index": int(idx),
                    "prediction_label": pred["prediction_label"],
                    "confidence_score": Decimal(str(round(pred["confidence_score"], 6))),
                    "created_at": now
                }
                predictions.append(pred_item)
                pred_table.put_item(Item=pred_item)
        elif data_type == "unstructured":
            data = json.loads(content_bytes.decode("utf-8"))
            chunks = data.get("chunks", [data.get("cleaned_text", "")])
            for idx, chunk in enumerate(chunks):
                pred = self.predict_text_single(chunk)
                pred_item = {
                    "prediction_id": f"{job_id}_{idx}",
                    "job_id": job_id,
                    "sample_index": int(idx),
                    "chunk_preview": chunk[:80],
                    "prediction_label": pred["prediction_label"],
                    "confidence_score": Decimal(str(round(pred["confidence_score"], 6))),
                    "created_at": now
                }
                predictions.append(pred_item)
                pred_table.put_item(Item=pred_item)

        else:
            raise ValueError("Unsupported data_type")

        # 2. Update DynamoDB Job status to INFERENCE_COMPLETED
        jobs_table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #st = :st, predictions_count = :pc, updated_at = :ua",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":st": "INFERENCE_COMPLETED",
                ":pc": len(predictions),
                ":ua": now
            }
        )

        return len(predictions)

inference_engine = InferenceEngine()
