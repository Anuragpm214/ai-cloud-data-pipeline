import io
import pandas as pd
import numpy as np

class StructuredTransformer:
    @staticmethod
    def transform(df: pd.DataFrame) -> tuple[bytes, dict]:
        """
        Clean, normalize, and transform structured data into optimized Parquet bytes.
        """
        transformed_df = df.copy()

        # 1. Clean column headers: strip whitespace, lowercase, replace spaces with underscores
        transformed_df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in transformed_df.columns]

        if transformed_df.columns.duplicated().any():
            raise ValueError("Column names collide after normalization")

        # 2. Impute numeric nulls with column median, categorical nulls with 'unknown'
        for col in transformed_df.columns:
            if pd.api.types.is_numeric_dtype(transformed_df[col]):
                transformed_df[col] = transformed_df[col].astype(float).replace([np.inf, -np.inf], np.nan)
                median_val = transformed_df[col].median()
                if not pd.isna(median_val):
                    transformed_df[col] = transformed_df[col].fillna(median_val)
                else:
                    transformed_df[col] = transformed_df[col].fillna(0)
            else:
                transformed_df[col] = transformed_df[col].fillna("unknown").astype(str)

        # 3. Serialize to Parquet format for fast cloud storage and analytics
        parquet_buffer = io.BytesIO()
        transformed_df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
        parquet_bytes = parquet_buffer.getvalue()

        metrics = {
            "processed_rows": int(len(transformed_df)),
            "processed_columns": int(len(transformed_df.columns)),
            "output_format": "parquet",
            "output_size_bytes": len(parquet_bytes)
        }

        return parquet_bytes, metrics
