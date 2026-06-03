import jwt
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from config import SECRET_KEY
import json

FEATURE_COLUMNS = [
    "age",
    "bmi",
    "temperature",
    "heart_rate",
    "bp_systolic",
    "bp_diastolic",
    "spo2",
    "fever",
    "cough",
    "chest_pain",
    "shortness_of_breath",
    "fatigue",
    "headache",
    "dizziness",
    "abdominal_pain",
    "joint_pain",
    "nausea",
    "weight_change",
]

SYMPTOM_COLUMNS = FEATURE_COLUMNS[7:]


# =========================================================
# PASSWORD UTILITIES
# =========================================================

def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# =========================================================
# JWT TOKEN UTILITIES
# =========================================================

def generate_token(user_id, role):
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=2)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# =========================================================
# ROLE BASED PROTECTION DECORATOR
# =========================================================

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = request.headers.get("Authorization")

            if not token:
                return jsonify({"error": "Token missing"}), 401

            if token.startswith("Bearer "):
                token = token.split(" ")[1]

            decoded = decode_token(token)

            if not decoded:
                return jsonify({"error": "Invalid or expired token"}), 401

            if decoded["role"] not in allowed_roles:
                return jsonify({"error": "Unauthorized access"}), 403

            request.user = decoded
            return f(*args, **kwargs)

        return wrapper
    return decorator


# =========================================================
# RISK LEVEL CALCULATION
# =========================================================

def calculate_risk(probability):
    if probability >= 0.80:
        return "High"
    elif probability >= 0.60:
        return "Medium"
    else:
        return "Low"


# =========================================================
# FEATURE EXTRACTION FOR ML
# =========================================================

def extract_features(data):
    """
    Converts frontend JSON into ML feature vector
    """

    patient = data.get("patient", {})
    vitals = data.get("vitals", {})
    symptoms = data.get("symptoms", [])

    symptom_features = [1 if s in symptoms else 0 for s in SYMPTOM_COLUMNS]

    def to_num(value):
        try:
            if value is None or value == "":
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    features = [
        to_num(patient.get("age", 0)),
        to_num(patient.get("bmi", 0)),
        to_num(vitals.get("temperature", 0)),
        to_num(vitals.get("heart_rate", 0)),
        to_num(vitals.get("bp_systolic", 0)),
        to_num(vitals.get("bp_diastolic", 0)),
        to_num(vitals.get("spo2", 0)),
    ] + symptom_features

    return features


# =========================================================
# AI EXPLANATION GENERATOR
# =========================================================

def generate_explanation(probability, symptoms):
    explanation = []

    if probability > 0.8:
        explanation.append("High probability based on critical symptom combination.")
    elif probability > 0.6:
        explanation.append("Moderate risk detected based on symptom severity.")
    else:
        explanation.append("Low probability based on current input values.")

    if symptoms:
        explanation.append(f"Key symptoms considered: {', '.join(symptoms)}")

    explanation.append("Vital parameters influenced ML decision boundary.")

    return explanation


# =========================================================
# AUDIT LOGGER
# =========================================================

def log_action(mysql, user_id, action, ip):
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO audit_logs (user_id, action, ip_address) VALUES (%s,%s,%s)",
            (user_id, action, ip)
        )
        mysql.connection.commit()
        cur.close()
    except:
        pass
