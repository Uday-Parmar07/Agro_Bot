import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

try:
    from xgboost import XGBClassifier
except ImportError as exc:
    raise SystemExit(
        "xgboost is not installed. Install it with: pip install xgboost"
    ) from exc


EXPECTED_COLUMNS = [
    "N",
    "P",
    "K",
    "temperature",
    "humidity",
    "ph",
    "rainfall",
    "label",
]


def clean_dataset(df: pd.DataFrame, k_max: float = 120.0) -> pd.DataFrame:
    """Clean crop recommendation data for model training."""
    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    cleaned = df[EXPECTED_COLUMNS].copy()
    cleaned = cleaned.drop_duplicates()

    feature_cols = [col for col in EXPECTED_COLUMNS if col != "label"]
    for col in feature_cols:
        cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    cleaned = cleaned.dropna(subset=EXPECTED_COLUMNS)

    # Constrain potassium values based on domain guidance.
    cleaned["K"] = cleaned["K"].clip(upper=k_max)

    # Truncate numeric values to 3 decimal places (not rounding).
    factor = 10**3
    cleaned[feature_cols] = np.trunc(cleaned[feature_cols] * factor) / factor

    return cleaned


def train_model(df: pd.DataFrame, test_size: float, random_state: int):
    feature_cols = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]

    X = df[feature_cols]
    y_raw = df["label"].astype(str)

    encoder = LabelEncoder()
    y = encoder.fit_transform(y_raw)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="multi:softprob",
        eval_metric="mlogloss",
        random_state=random_state,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)
    report = classification_report(
        y_test,
        predictions,
        target_names=encoder.classes_,
        output_dict=True,
        zero_division=0,
    )

    return model, encoder, feature_cols, accuracy, report


def main():
    parser = argparse.ArgumentParser(
        description="Clean crop recommendation data and train an XGBoost model."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("Dataset/Crop_recommendation.csv"),
        help="Path to raw crop recommendation CSV.",
    )
    parser.add_argument(
        "--cleaned-output",
        type=Path,
        default=Path("Dataset/Crop_recommendation_cleaned_xgb.csv"),
        help="Path to save cleaned CSV.",
    )
    parser.add_argument(
        "--model-output",
        type=Path,
        default=Path("artifacts/xgboost_crop_model.joblib"),
        help="Path to save trained model artifact.",
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("artifacts/xgboost_crop_metrics.json"),
        help="Path to save evaluation metrics JSON.",
    )
    parser.add_argument(
        "--k-max",
        type=float,
        default=120.0,
        help="Upper cap for K column values.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Test split ratio.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input dataset not found: {args.input}")

    raw_df = pd.read_csv(args.input)
    cleaned_df = clean_dataset(raw_df, k_max=args.k_max)

    args.cleaned_output.parent.mkdir(parents=True, exist_ok=True)
    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)

    cleaned_df.to_csv(args.cleaned_output, index=False)

    model, encoder, feature_cols, accuracy, report = train_model(
        cleaned_df,
        test_size=args.test_size,
        random_state=args.random_state,
    )

    joblib.dump(
        {
            "model": model,
            "label_encoder": encoder,
            "feature_columns": feature_cols,
        },
        args.model_output,
    )

    metrics_payload = {
        "rows_raw": int(len(raw_df)),
        "rows_cleaned": int(len(cleaned_df)),
        "k_max_applied": args.k_max,
        "test_size": args.test_size,
        "random_state": args.random_state,
        "accuracy": float(accuracy),
        "classification_report": report,
    }

    with args.metrics_output.open("w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)

    print("Training complete")
    print(f"Raw rows         : {len(raw_df)}")
    print(f"Cleaned rows     : {len(cleaned_df)}")
    print(f"Accuracy         : {accuracy:.4f}")
    print(f"Cleaned CSV      : {args.cleaned_output}")
    print(f"Model artifact   : {args.model_output}")
    print(f"Metrics artifact : {args.metrics_output}")


if __name__ == "__main__":
    main()
