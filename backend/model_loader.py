import joblib
import os
import numpy as np

MODELS = {}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_models():
    diseases = ["diabetes", "heart", "respiratory", "kidney", "liver", "cancer"]
    for d in diseases:
        path = os.path.join(BASE_DIR, "models", f"{d}.pkl")
        loaded = joblib.load(path)

        # Backward compatibility: older files store estimator directly.
        if isinstance(loaded, dict) and "model" in loaded:
            MODELS[d] = loaded
        else:
            MODELS[d] = {"model": loaded, "feature_names": None, "metrics": None}

def predict(disease, features):
    if disease not in MODELS:
        raise ValueError(f"Unsupported disease target: {disease}")
    artifact = MODELS[disease]
    model = artifact["model"]

    features = np.array(features, dtype=float).reshape(1, -1)

    if artifact.get("feature_names"):
        expected = len(artifact["feature_names"])
        if features.shape[1] != expected:
            raise ValueError(f"Expected {expected} input features, received {features.shape[1]}")

    prediction = int(model.predict(features)[0])

    # Use positive-class probability for medical risk scoring.
    # Fallback to max probability if class mapping is unavailable.
    proba = model.predict_proba(features)[0]
    if hasattr(model, "classes_") and 1 in model.classes_:
        pos_idx = list(model.classes_).index(1)
        prob = float(proba[pos_idx])
    else:
        prob = float(np.max(proba))

    return prediction, prob
