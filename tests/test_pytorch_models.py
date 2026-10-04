import pytest
import sys
import os
import torch


from services.ai_inference.src.models.pytorch_models import TabularClassifier, TextEmbeddingClassifier
from services.ai_inference.src.pipelines.inference_engine import inference_engine

def test_tabular_model_forward():
    model = TabularClassifier(input_dim=4, hidden_dim=16, num_classes=2)
    model.eval()

    dummy_input = torch.tensor([[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]], dtype=torch.float32)
    with torch.no_grad():
        out = model(dummy_input)

    assert out.shape == (2, 2)
    probs = torch.softmax(out, dim=1)
    assert probs.shape == (2, 2)
    assert torch.allclose(probs.sum(dim=1), torch.ones(2))

def test_text_model_forward():
    model = TextEmbeddingClassifier(vocab_size=100, embed_dim=16, num_classes=3)
    model.eval()

    dummy_tokens = torch.tensor([1, 10, 4, 20], dtype=torch.long)
    offsets = torch.tensor([0], dtype=torch.long)

    with torch.no_grad():
        out = model(dummy_tokens, offsets)

    assert out.shape == (1, 3)

def test_inference_engine_single_predictions():
    # Test tabular single
    tab_res = inference_engine.predict_tabular_single([1.0, 2.0, 3.0, 4.0])
    assert "prediction_label" in tab_res
    assert "confidence_score" in tab_res
    assert 0.0 <= tab_res["confidence_score"] <= 1.0

    # Test text single
    txt_res = inference_engine.predict_text_single("Scalable cloud data pipelines are amazing.")
    assert "prediction_label" in txt_res
    assert "confidence_score" in txt_res
    assert 0.0 <= txt_res["confidence_score"] <= 1.0
