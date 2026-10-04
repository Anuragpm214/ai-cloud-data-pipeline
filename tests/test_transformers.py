import io
import pandas as pd
import json
import pytest
import sys
import os

# Add service paths

from services.pipeline_worker.src.validators.data_validator import DataValidator
from services.pipeline_worker.src.transformers.structured import StructuredTransformer
from services.pipeline_worker.src.transformers.unstructured import UnstructuredTransformer

def test_tabular_validation_and_transform():
    csv_content = b"user_id,age,income,is_active\n1,25,50000,true\n2,,60000,false\n3,40,,true\n"
    is_valid, df, profile = DataValidator.validate_tabular_data(csv_content, "test.csv")

    assert is_valid is True
    assert profile["num_rows"] == 3
    assert profile["num_columns"] == 4

    parquet_bytes, metrics = StructuredTransformer.transform(df)
    assert metrics["processed_rows"] == 3
    assert metrics["output_format"] == "parquet"
    assert len(parquet_bytes) > 0

    # Read back parquet
    read_df = pd.read_parquet(io.BytesIO(parquet_bytes))
    assert len(read_df) == 3
    # Missing numeric values should be imputed
    assert read_df["age"].isnull().sum() == 0

def test_unstructured_validation_and_transform():
    text_content = b"Antigravity AI Cloud Pipeline. High performance scalable architecture! Event-driven processing."
    is_valid, text, profile = DataValidator.validate_text_data(text_content)

    assert is_valid is True
    assert profile["word_count"] > 5

    output_bytes, metrics = UnstructuredTransformer.transform_text(text)
    assert metrics["chunks_count"] >= 2

    parsed = json.loads(output_bytes.decode("utf-8"))
    assert "cleaned_text" in parsed
    assert len(parsed["chunks"]) >= 2


def test_categorical_nulls_and_nonfinite_numbers():
    df = pd.DataFrame({'Label': ['a', None], 'Value': [float('inf'), 2.0]})
    payload, _ = StructuredTransformer.transform(df)
    cleaned = pd.read_parquet(io.BytesIO(payload))
    assert cleaned['label'].tolist() == ['a', 'unknown']
    assert cleaned['value'].tolist() == [2.0, 2.0]


def test_colliding_column_names_rejected():
    with pytest.raises(ValueError, match='collide'):
        StructuredTransformer.transform(pd.DataFrame({'A B': [1], 'a-b': [2]}))


def test_invalid_utf8_rejected():
    assert not DataValidator.validate_text_data(b'hello\xff')[0]
