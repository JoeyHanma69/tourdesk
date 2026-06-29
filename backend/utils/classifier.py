"""
backend/utils/classifier.py
============================
Loads the fine-tuned DistilBERT model once at app startup.
All routes call app.classifier.predict(text) — never reload per request.
"""

import os
import sys
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    text: str
    label: str          # "Automated" | "Assisted" | "Escalate"
    confidence: float   # 0.0 – 1.0
    uncertain: bool     # True if below threshold
    all_scores: dict    # {"Automated": 0.9, "Assisted": 0.05, "Escalate": 0.05}


class TourDeskClassifier:
    """Wraps the HuggingFace pipeline. Thread-safe for Flask."""

    def __init__(self, model_dir: str, threshold: float = 0.65):
        self.model_dir = model_dir
        self.threshold = threshold
        self._pipeline = None
        self._load()

    def _load(self):
        if not os.path.isdir(self.model_dir):
            logger.warning(
                f"⚠️  Model not found at '{self.model_dir}'. "
                "Running in STUB MODE — predictions will return placeholder values. "
                "Download the model from Google Drive and set MODEL_DIR in .env."
            )
            self._pipeline = None
            return

        required = ["config.json", "model.safetensors", "tokenizer.json"]
        missing = [f for f in required if not os.path.exists(os.path.join(self.model_dir, f))]
        if missing:
            logger.warning(f"⚠️  Incomplete model files {missing}. Running in STUB MODE.")
            self._pipeline = None
            return

        try:
            from transformers import pipeline
            self._pipeline = pipeline(
                "text-classification",
                model=self.model_dir,
                tokenizer=self.model_dir,
                device=-1,    # CPU; change to 0 for local GPU
                top_k=None,
            )
            logger.info(f"✅ Classifier loaded from {self.model_dir}")
        except Exception as e:
            logger.error(f"Failed to load classifier: {e}")
            self._pipeline = None

    def predict(self, text: str) -> Prediction:
        text = str(text).strip()

        # Stub mode — model not downloaded yet
        if self._pipeline is None:
            return Prediction(
                text=text,
                label="Automated",
                confidence=0.0,
                uncertain=True,
                all_scores={"Automated": 0.0, "Assisted": 0.0, "Escalate": 0.0},
            )

        results = self._pipeline(text, truncation=True, max_length=128)[0]
        top = max(results, key=lambda x: x["score"])
        all_scores = {r["label"]: round(r["score"], 4) for r in results}

        return Prediction(
            text=text,
            label=top["label"],
            confidence=round(top["score"], 4),
            uncertain=top["score"] < self.threshold,
            all_scores=all_scores,
        )

    @property
    def is_ready(self) -> bool:
        return self._pipeline is not None
