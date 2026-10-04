import io
import pandas as pd
from typing import Dict, Any, Tuple

class DataValidator:
    @staticmethod
    def validate_tabular_data(raw_bytes: bytes, filename: str) -> Tuple[bool, pd.DataFrame, Dict[str, Any]]:
        """Validate CSV / JSON tabular data structure and profile metrics."""
        try:
            filename = filename.lower()
            if filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(raw_bytes))
            elif filename.endswith(".json"):
                df = pd.read_json(io.BytesIO(raw_bytes))
            elif filename.endswith(".parquet"):
                df = pd.read_parquet(io.BytesIO(raw_bytes))
            else:
                # Default CSV fallback
                df = pd.read_csv(io.BytesIO(raw_bytes))

            if df.empty:
                return False, df, {"error": "Dataset is empty"}

            profile = {
                "num_rows": int(len(df)),
                "num_columns": int(len(df.columns)),
                "columns": list(df.columns),
                "null_counts": {col: int(df[col].isnull().sum()) for col in df.columns},
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()}
            }
            return True, df, profile
        except Exception as e:
            return False, pd.DataFrame(), {"error": f"Tabular validation failed: {str(e)}"}

    @staticmethod
    def validate_text_data(raw_bytes: bytes) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate unstructured text data."""
        try:
            text = raw_bytes.decode("utf-8", errors="strict").strip()
            if not text:
                return False, "", {"error": "Text content is empty"}

            profile = {
                "character_count": len(text),
                "word_count": len(text.split()),
                "lines_count": len(text.splitlines())
            }
            return True, text, profile
        except Exception as e:
            return False, "", {"error": f"Text validation failed: {str(e)}"}
