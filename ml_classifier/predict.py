"""
predict.py — TourDesk AI Inference Script
==========================================
Runs the fine-tuned DistilBERT classifier on one or more guest messages.

Usage:
    # Single message
    python predict.py --message "What time does the tour start?"

    # Batch from CSV (must have a 'text' column)
    python predict.py --file messages.csv --output results.csv

    # Change model path (default: ml_classifier/model/)
    python predict.py --message "Hello" --model path/to/model
"""

import argparse
import os
import sys

import pandas as pd
from transformers import pipeline


# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
CONFIDENCE_THRESHOLD = 0.65   # predictions below this are flagged as uncertain
MAX_LEN = 128


# ── Load model ────────────────────────────────────────────────────────────────
def load_classifier(model_dir: str):
    if not os.path.isdir(model_dir):
        print(f"\n❌  Model directory not found: {model_dir}")
        print("    Did you complete Step 5 in the README? (Download model from Google Drive)")
        sys.exit(1)

    required = ["config.json", "model.safetensors", "tokenizer.json"]
    missing = [f for f in required if not os.path.exists(os.path.join(model_dir, f))]
    if missing:
        print(f"\n❌  Missing model files: {missing}")
        print("    Re-download the model folder from Google Drive (see README Step 5).")
        sys.exit(1)

    print(f"Loading model from: {model_dir}")
    clf = pipeline(
        "text-classification",
        model=model_dir,
        tokenizer=model_dir,
        device=-1,           # CPU on desktop; change to 0 if you have a local GPU
        top_k=None,          # return scores for all classes
    )
    print("✅ Model loaded\n")
    return clf


# ── Predict ───────────────────────────────────────────────────────────────────
def predict_one(clf, message: str) -> dict:
    results = clf(message, truncation=True, max_length=MAX_LEN)[0]
    # results is a list of {label, score} dicts — pick the top one
    top = max(results, key=lambda x: x["score"])
    all_scores = {r["label"]: round(r["score"], 4) for r in results}
    uncertain = top["score"] < CONFIDENCE_THRESHOLD
    return {
        "message":    message,
        "predicted":  top["label"],
        "confidence": f"{top['score']:.2%}",
        "uncertain":  uncertain,
        "all_scores": all_scores,
    }


def predict_batch(clf, df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, row in df.iterrows():
        text = str(row["text"]).strip()
        if not text:
            continue
        result = predict_one(clf, text)
        rows.append({
            "text":       text,
            "predicted":  result["predicted"],
            "confidence": result["confidence"],
            "uncertain":  result["uncertain"],
        })
    return pd.DataFrame(rows)


# ── Display ───────────────────────────────────────────────────────────────────
def print_result(result: dict):
    uncertain_flag = "  ⚠️  LOW CONFIDENCE — recommend human review" if result["uncertain"] else ""
    print("─" * 60)
    print(f"  Message   : {result['message'][:80]}")
    print(f"  Predicted : {result['predicted']}")
    print(f"  Confidence: {result['confidence']}{uncertain_flag}")
    print(f"  All scores: {result['all_scores']}")
    print("─" * 60)


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="TourDesk AI — Guest Message Classifier")
    parser.add_argument("--message", type=str, help="Single message to classify")
    parser.add_argument("--file",    type=str, help="CSV file with a 'text' column")
    parser.add_argument("--output",  type=str, help="Save batch results to this CSV file")
    parser.add_argument("--model",   type=str, default=DEFAULT_MODEL_DIR, help="Path to model directory")
    args = parser.parse_args()

    if not args.message and not args.file:
        parser.print_help()
        sys.exit(1)

    clf = load_classifier(args.model)

    if args.message:
        result = predict_one(clf, args.message)
        print_result(result)

    if args.file:
        if not os.path.exists(args.file):
            print(f"❌  File not found: {args.file}")
            sys.exit(1)
        df = pd.read_csv(args.file)
        if "text" not in df.columns:
            print("❌  CSV must have a 'text' column.")
            sys.exit(1)
        print(f"Running predictions on {len(df)} messages...")
        results_df = predict_batch(clf, df)
        if args.output:
            results_df.to_csv(args.output, index=False)
            print(f"✅  Results saved to: {args.output}")
        else:
            print(results_df.to_string(index=False))


if __name__ == "__main__":
    main()
