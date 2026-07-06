"""
Intent classifier using TF-IDF + Logistic Regression.

Trained on a small labeled dataset of loan chatbot utterances.
Falls back to rule-based detection when confidence is below threshold.
"""

import os
import json
from enum import Enum
from typing import Tuple

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "intent_model.pkl")
TRAINING_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "intent_training.json")

CONFIDENCE_THRESHOLD = 0.55


class Intent(str, Enum):
    PROVIDE_PAN = "provide_pan"
    PROVIDE_INCOME = "provide_income"
    PROVIDE_LOAN_AMOUNT = "provide_loan_amount"
    CONFIRM = "confirm"
    DENY = "deny"
    MODIFY = "modify"
    ASK_QUESTION = "ask_question"
    GREETING = "greeting"
    FRUSTRATED = "frustrated"
    OUT_OF_SCOPE = "out_of_scope"


class IntentClassifier:
    def __init__(self):
        self.pipeline: Pipeline | None = None
        self._load_or_train()

    def _load_or_train(self):
        if os.path.exists(MODEL_PATH):
            self.pipeline = joblib.load(MODEL_PATH)
        else:
            self.train()

    def train(self):
        with open(TRAINING_DATA_PATH, "r") as f:
            data = json.load(f)

        texts = [item["text"] for item in data]
        labels = [item["intent"] for item in data]

        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=5000,
                lowercase=True,
                strip_accents="unicode",
            )),
            ("clf", LogisticRegression(
                max_iter=1000,
                C=5.0,
                class_weight="balanced",
            )),
        ])

        self.pipeline.fit(texts, labels)

        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(self.pipeline, MODEL_PATH)

    def predict(self, text: str) -> Tuple[Intent, float]:
        if self.pipeline is None:
            return Intent.OUT_OF_SCOPE, 0.0

        proba = self.pipeline.predict_proba([text])[0]
        max_idx = np.argmax(proba)
        confidence = proba[max_idx]
        intent_label = self.pipeline.classes_[max_idx]

        try:
            intent = Intent(intent_label)
        except ValueError:
            intent = Intent.OUT_OF_SCOPE

        if confidence < CONFIDENCE_THRESHOLD:
            return Intent.OUT_OF_SCOPE, confidence

        return intent, float(confidence)

    def predict_top_n(self, text: str, n: int = 3) -> list[Tuple[Intent, float]]:
        if self.pipeline is None:
            return [(Intent.OUT_OF_SCOPE, 0.0)]

        proba = self.pipeline.predict_proba([text])[0]
        top_indices = np.argsort(proba)[::-1][:n]

        results = []
        for idx in top_indices:
            try:
                intent = Intent(self.pipeline.classes_[idx])
            except ValueError:
                intent = Intent.OUT_OF_SCOPE
            results.append((intent, float(proba[idx])))

        return results
