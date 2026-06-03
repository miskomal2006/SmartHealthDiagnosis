import json
import os
from datetime import datetime

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from utils import FEATURE_COLUMNS

DISEASES = ["diabetes", "heart", "respiratory", "kidney", "liver", "cancer"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "..", "dataset")
MODELS_DIR = os.path.join(BASE_DIR, "models")
REPORT_DIR = os.path.join(BASE_DIR, "model_reports")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)


def build_candidates():
    return [
        (
            "logreg",
            Pipeline(
                [
                    ("scaler", StandardScaler()),
                    (
                        "clf",
                        LogisticRegression(
                            class_weight="balanced",
                            max_iter=2000,
                            solver="liblinear",
                            random_state=42,
                        ),
                    ),
                ]
            ),
            {
                "clf__C": [0.25, 0.5, 1.0, 2.0, 4.0],
            },
        ),
        (
            "rf",
            RandomForestClassifier(
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            ),
            {
                "n_estimators": [200, 300],
                "max_depth": [8, 12, None],
                "min_samples_leaf": [1, 2, 4],
            },
        ),
    ]


def train_one(disease):
    path = os.path.join(DATASET_DIR, f"{disease}.csv")
    df = pd.read_csv(path)

    missing = [c for c in FEATURE_COLUMNS + ["target"] if c not in df.columns]
    if missing:
        raise ValueError(f"{disease}: missing required columns: {missing}")

    X = df[FEATURE_COLUMNS].copy()
    y = df["target"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        stratify=y,
        random_state=42,
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    best_name = None
    best_model = None
    best_f1 = -1.0

    for name, estimator, param_grid in build_candidates():
        gs = GridSearchCV(
            estimator=estimator,
            param_grid=param_grid,
            scoring="f1",
            cv=cv,
            n_jobs=-1,
            refit=True,
        )
        gs.fit(X_train, y_train)
        if gs.best_score_ > best_f1:
            best_f1 = float(gs.best_score_)
            best_name = name
            best_model = gs.best_estimator_

    calibrated = CalibratedClassifierCV(best_model, method="sigmoid", cv=3)
    calibrated.fit(X_train, y_train)

    y_pred = calibrated.predict(X_test)
    y_prob = calibrated.predict_proba(X_test)[:, 1]

    metrics = {
        "model_family": best_name,
        "cv_best_f1": round(best_f1, 4),
        "test_accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "test_precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "test_recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "test_f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "test_roc_auc": round(float(roc_auc_score(y_test, y_prob)), 4),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, zero_division=0, output_dict=True),
        "trained_at_utc": datetime.utcnow().isoformat() + "Z",
    }

    artifact = {
        "model": calibrated,
        "feature_names": FEATURE_COLUMNS,
        "metrics": metrics,
    }

    model_out = os.path.join(MODELS_DIR, f"{disease}.pkl")
    joblib.dump(artifact, model_out)

    report_out = os.path.join(REPORT_DIR, f"{disease}_report.json")
    with open(report_out, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"[{disease}] model={best_name} f1={metrics['test_f1']} auc={metrics['test_roc_auc']}")


def main():
    for disease in DISEASES:
        train_one(disease)
    print("Training completed.")


if __name__ == "__main__":
    main()
