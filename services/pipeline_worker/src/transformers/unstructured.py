import re
import json

class UnstructuredTransformer:
    @staticmethod
    def transform_text(text: str) -> tuple[bytes, dict]:
        """
        Clean, normalize, and tokenize unstructured text.
        """
        # Normalize whitespace and strip special non-printable characters
        cleaned_text = re.sub(r'\s+', ' ', text).strip()

        # Split into sentence/paragraph chunks
        sentences = [s.strip() for s in re.split(r'[.!?]+', cleaned_text) if s.strip()]

        payload = {
            "cleaned_text": cleaned_text,
            "chunks": sentences,
            "total_chunks": len(sentences)
        }

        output_bytes = json.dumps(payload, indent=2).encode("utf-8")

        metrics = {
            "cleaned_char_count": len(cleaned_text),
            "chunks_count": len(sentences),
            "output_format": "json",
            "output_size_bytes": len(output_bytes)
        }

        return output_bytes, metrics
