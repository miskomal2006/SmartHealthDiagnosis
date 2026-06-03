from pdf_generator import generate_pdf
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_mysqldb import MySQL
from config import *
from model_loader import load_models, predict, MODELS
from utils import (
    hash_password,
    verify_password,
    generate_token,
    role_required,
    calculate_risk,
    extract_features,
    generate_explanation,
    log_action
)
import json

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ================= DATABASE CONFIG =================
app.config["MYSQL_HOST"] = MYSQL_HOST
app.config["MYSQL_USER"] = MYSQL_USER
app.config["MYSQL_PASSWORD"] = MYSQL_PASSWORD
app.config["MYSQL_DB"] = MYSQL_DB
app.config["SECRET_KEY"] = SECRET_KEY

mysql = MySQL(app)

# Load ML models
load_models()


def ensure_schema_updates():
    cur = mysql.connection.cursor()
    try:
        try:
            cur.execute("""
                ALTER TABLE diagnosis_records
                ADD COLUMN IF NOT EXISTS patient_deleted TINYINT(1) DEFAULT 0
            """)
            mysql.connection.commit()
        except Exception:
            cur.execute("""
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=%s
                  AND TABLE_NAME='diagnosis_records'
                  AND COLUMN_NAME='patient_deleted'
            """, (MYSQL_DB,))
            exists = cur.fetchone()[0] > 0
            if not exists:
                cur.execute("""
                    ALTER TABLE diagnosis_records
                    ADD COLUMN patient_deleted TINYINT(1) DEFAULT 0
                """)
                mysql.connection.commit()

        try:
            cur.execute("""
                ALTER TABLE diagnosis_records
                ADD COLUMN IF NOT EXISTS patient_display_name VARCHAR(150) NULL
            """)
            mysql.connection.commit()
        except Exception:
            cur.execute("""
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=%s
                  AND TABLE_NAME='diagnosis_records'
                  AND COLUMN_NAME='patient_display_name'
            """, (MYSQL_DB,))
            exists = cur.fetchone()[0] > 0
            if not exists:
                cur.execute("""
                    ALTER TABLE diagnosis_records
                    ADD COLUMN patient_display_name VARCHAR(150) NULL
                """)
                mysql.connection.commit()
    finally:
        cur.close()


with app.app_context():
    ensure_schema_updates()

# =====================================================
# REGISTER (Creates user + patient profile if patient)
# =====================================================
from validators import RegisterSchema, LoginSchema, DiagnosisSchema
from marshmallow import ValidationError

@app.route("/api/register", methods=["POST"])
def register():
    try:
        data = RegisterSchema().load(request.json)
    except ValidationError as err:
        return jsonify({"error": err.messages}), 400

    cur = mysql.connection.cursor()

    # Check duplicate email
    cur.execute("SELECT id FROM users WHERE LOWER(email)=LOWER(%s)", (data["email"],))
    if cur.fetchone():
        cur.close()
        return jsonify({"error": "Email already registered"}), 400

    hashed = hash_password(data["password"])

    cur.execute("""
        INSERT INTO users (full_name,email,password_hash,role)
        VALUES (%s,%s,%s,%s)
    """, (data["name"], data["email"], hashed.decode(), data["role"]))
    user_id = cur.lastrowid

    # Create a basic patient profile row for patient accounts.
    if data["role"] == "patient":
        cur.execute("INSERT INTO patient_profiles (user_id) VALUES (%s)", (user_id,))

    mysql.connection.commit()
    cur.close()

    return jsonify({"message": "User registered successfully"})


# =====================================================
# LOGIN
# =====================================================
@app.route("/api/login", methods=["POST"])
def login():
    try:
        data = LoginSchema().load(request.json)
    except ValidationError as err:
        return jsonify({"error": err.messages}), 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE LOWER(email)=LOWER(%s)", (data["email"],))
    user = cur.fetchone()
    cur.close()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if not user[5]:
        return jsonify({"error": "Account blocked by admin"}), 403

    if verify_password(data["password"], user[3]):
        token = generate_token(user[0], user[4])
        return jsonify({
            "token": token,
            "role": user[4],
            "name": user[1]
        })

    return jsonify({"error": "Invalid credentials"}), 401


# =====================================================
# UPDATE PATIENT PROFILE
# =====================================================
@app.route("/api/patient/profile", methods=["PUT"])
@role_required(["patient"])
def update_profile():
    data = request.json
    user_id = request.user["user_id"]

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE patient_profiles
        SET age=%s, gender=%s, blood_group=%s,
            height=%s, weight=%s, bmi=%s, location=%s
        WHERE user_id=%s
    """, (
        data.get("age"),
        data.get("gender"),
        data.get("blood_group"),
        data.get("height"),
        data.get("weight"),
        data.get("bmi"),
        data.get("location"),
        user_id
    ))
    if cur.rowcount == 0:
        cur.execute("""
            INSERT INTO patient_profiles (user_id, age, gender, blood_group, height, weight, bmi, location)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            user_id,
            data.get("age"),
            data.get("gender"),
            data.get("blood_group"),
            data.get("height"),
            data.get("weight"),
            data.get("bmi"),
            data.get("location"),
        ))

    mysql.connection.commit()
    cur.close()

    return jsonify({"message": "Profile updated"})

@app.route("/api/report/<int:diagnosis_id>", methods=["DELETE"])
@role_required(["patient"])
def delete_report(diagnosis_id):
    user_id = request.user["user_id"]
    cur = mysql.connection.cursor()

    # Patient delete should only hide from patient dashboard, not remove data for admin/doctor.
    cur.execute("""
        SELECT id FROM diagnosis_records
        WHERE id=%s AND patient_id=%s
    """, (diagnosis_id, user_id))
    if not cur.fetchone():
        cur.close()
        return jsonify({"error": "Report not found"}), 404

    cur.execute("""
        UPDATE diagnosis_records
        SET patient_deleted=1
        WHERE id=%s AND patient_id=%s
    """, (diagnosis_id, user_id))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Report removed from your dashboard"})

@app.route("/api/doctor/cases", methods=["GET"])
@role_required(["doctor"])
def doctor_cases():

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT d.id, u.full_name, d.predicted_disease, d.risk_level
        FROM diagnosis_records d
        JOIN users u ON d.patient_id = u.id
        ORDER BY d.created_at DESC
    """)

    rows = cur.fetchall()
    cur.close()

    cases = []

    for r in rows:
        cases.append({
            "id": r[0],
            "patient_name": r[1],
            "disease": r[2],
            "risk": r[3]
        })

    return jsonify({"cases": cases})


# =====================================================
# PREDICT & SAVE FULL DIAGNOSIS
# =====================================================
@app.route("/api/predict", methods=["POST"])
@role_required(["patient"])
def predict_disease():

    try:
        data = DiagnosisSchema().load(request.json)
    except ValidationError as err:
        return jsonify({"error": err.messages}), 400

    user_id = request.user["user_id"]
    disease_type = data["disease_target"]

    features = extract_features(data)
    try:
        prediction, prob = predict(disease_type, features)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400

    if prediction == 1:
        final_disease = disease_type.upper() + " POSITIVE"
    else:
        final_disease = "No Significant " + disease_type.upper() + " Risk"

    risk_level = calculate_risk(prob)
    explanation = generate_explanation(prob, data.get("symptoms", []))

    cur = mysql.connection.cursor()

    patient_payload = data.get("patient", {})
    cur.execute("SELECT id FROM patient_profiles WHERE user_id=%s LIMIT 1", (user_id,))
    profile = cur.fetchone()
    if profile:
        cur.execute("""
            UPDATE patient_profiles
            SET age=%s, gender=%s, bmi=%s, blood_group=%s, location=%s, height=%s, weight=%s
            WHERE id=%s
        """, (
            patient_payload.get("age"),
            patient_payload.get("gender"),
            patient_payload.get("bmi"),
            patient_payload.get("blood_group"),
            patient_payload.get("location"),
            patient_payload.get("height"),
            patient_payload.get("weight"),
            profile[0],
        ))
    else:
        cur.execute("""
            INSERT INTO patient_profiles (user_id, age, gender, bmi, blood_group, location, height, weight)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            patient_payload.get("age"),
            patient_payload.get("gender"),
            patient_payload.get("bmi"),
            patient_payload.get("blood_group"),
            patient_payload.get("location"),
            patient_payload.get("height"),
            patient_payload.get("weight"),
        ))

    cur.execute("""
        INSERT INTO diagnosis_records
        (patient_id,patient_display_name,disease_target,predicted_disease,
         confidence,risk_level,severity_level,
         duration_days,medical_history,
         smoking_status,alcohol_status,
         physical_activity,sleep_hours,
         stress_level,ai_explanation,model_version)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        user_id,
        patient_payload.get("full_name") or None,
        disease_type,
        final_disease,   # FIXED
        round(prob * 100, 2),
        risk_level,
        data["metadata"].get("severity"),
        data["metadata"].get("duration_days"),
        data.get("medicalHistory"),
        data.get("smoking"),
        data.get("alcohol"),
        data.get("activity"),
        data.get("sleep"),
        data.get("stress"),
        json.dumps(explanation),
        "v1.0"
    ))

    diagnosis_id = cur.lastrowid

    # SAVE VITALS
    vitals = data.get("vitals", {})
    cur.execute("""
        INSERT INTO vital_signs
        (diagnosis_id, temperature, heart_rate,
         bp_systolic, bp_diastolic, respiratory_rate, spo2)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        diagnosis_id,
        vitals.get("temperature"),
        vitals.get("heart_rate"),
        vitals.get("bp_systolic"),
        vitals.get("bp_diastolic"),
        vitals.get("respRate"),
        vitals.get("spo2")
    ))

    # SAVE SYMPTOMS
    for symptom in data.get("symptoms", []):
        cur.execute("SELECT id FROM symptoms WHERE name=%s", (symptom,))
        s = cur.fetchone()
        if s:
            cur.execute("""
                INSERT INTO diagnosis_symptoms (diagnosis_id, symptom_id)
                VALUES (%s,%s)
            """, (diagnosis_id, s[0]))

    mysql.connection.commit()
    cur.close()

    return jsonify({
        "predicted_disease": final_disease,
        "confidence": round(prob * 100, 2),
        "risk_level": risk_level,
        "explanation": explanation,
        "diagnosis_id": diagnosis_id
    })



# =====================================================
# GET FULL DIAGNOSIS HISTORY (PATIENT)
# =====================================================
@app.route("/api/history", methods=["GET"])
@role_required(["patient"])
def history():
    user_id = request.user["user_id"]

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id,predicted_disease,confidence,
               risk_level,created_at
        FROM diagnosis_records
        WHERE patient_id=%s
          AND COALESCE(patient_deleted, 0)=0
        ORDER BY created_at DESC
    """, (user_id,))
    records = cur.fetchall()
    cur.close()

    return jsonify({"history": records})

@app.route("/api/patient/suggestions", methods=["GET"])
@role_required(["patient"])
def patient_suggestions():
    user_id = request.user["user_id"]
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT ds.diagnosis_id,
               d.predicted_disease,
               ds.suggestion,
               u.full_name,
               ds.created_at
        FROM doctor_suggestions ds
        JOIN diagnosis_records d ON ds.diagnosis_id = d.id
        JOIN users u ON ds.doctor_id = u.id
        WHERE d.patient_id=%s
        ORDER BY ds.created_at DESC
    """, (user_id,))
    suggestions = cur.fetchall()
    cur.close()
    return jsonify({"suggestions": suggestions})


# =====================================================
# DOCTOR SUGGESTION
# =====================================================
@app.route("/api/doctor/suggest/<int:diagnosis_id>", methods=["POST"])
@role_required(["doctor"])
def suggest(diagnosis_id):
    doctor_id = request.user["user_id"]
    data = request.json

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO doctor_suggestions
        (diagnosis_id,doctor_id,suggestion)
        VALUES (%s,%s,%s)
    """, (diagnosis_id, doctor_id, data["suggestion"]))

    mysql.connection.commit()
    cur.close()

    return jsonify({"message": "Suggestion saved"})


# =====================================================
# ADMIN DASHBOARD DATA
# =====================================================
@app.route("/api/admin/overview", methods=["GET"])
@role_required(["admin"])
def admin_overview():
    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM diagnosis_records")
    total_diagnosis = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE role='patient'")
    patients = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE role='doctor'")
    doctors = cur.fetchone()[0]

    cur.close()

    return jsonify({
        "total_users": total_users,
        "patients": patients,
        "doctors": doctors,
        "total_diagnosis": total_diagnosis
    })


# =====================================================
# GENERATE PDF REPORT
# =====================================================
@app.route("/api/report/<int:diagnosis_id>", methods=["GET"])
@role_required(["patient","doctor","admin"])
def generate_report(diagnosis_id):
    cur = mysql.connection.cursor()

    # Fetch diagnosis
    cur.execute("""
                SELECT d.id,
                d.patient_id,
                COALESCE(NULLIF(d.patient_display_name, ''), u.full_name) AS patient_name,
                p.age,
                p.gender,
                p.bmi,
                p.blood_group,
                p.location,
                d.predicted_disease,
                d.confidence,
                d.risk_level,
                d.ai_explanation,
                d.medical_history,
                d.severity_level,
                d.duration_days,
                d.created_at
                FROM diagnosis_records d
                JOIN users u ON d.patient_id = u.id
                LEFT JOIN patient_profiles p ON p.user_id = u.id
                WHERE d.id = %s
                """, (diagnosis_id,))

    diag = cur.fetchone()

    if not diag:
        cur.close()
        return jsonify({"error": "Report not found"}), 404
    # ================= AUTHORIZATION CHECK =================
    diag_patient_id = diag[1]
    if request.user["role"] == "patient":
        if request.user["user_id"] != diag_patient_id:
            cur.close()
            return jsonify({"error": "Unauthorized access"}), 403


    # Fetch vitals
    cur.execute("""
        SELECT temperature,heart_rate,
               bp_systolic,bp_diastolic,respiratory_rate,spo2
        FROM vital_signs WHERE diagnosis_id=%s
    """, (diagnosis_id,))
    vitals = cur.fetchone()

    # Fetch symptoms
    cur.execute("""
        SELECT s.name FROM diagnosis_symptoms ds
        JOIN symptoms s ON ds.symptom_id=s.id
        WHERE ds.diagnosis_id=%s
    """, (diagnosis_id,))
    symptoms = [row[0] for row in cur.fetchall()]

    cur.close()

    report_data = {
    "patient": {
        "name": diag[2],
        "age": diag[3] or "N/A",
        "gender": diag[4] or "N/A",
        "bmi": diag[5] or "N/A",
        "blood_group": diag[6] or "N/A",
        "location": diag[7] or "N/A",
        "date": diag[15].strftime("%d %B %Y")
    },
    "prediction": {
        "disease": diag[8],
        "confidence": diag[9],
        "risk_level": diag[10]
    },
    "medical_history": diag[12] or "Not Provided",
    "severity": diag[13] or "N/A",
    "duration": diag[14] or "N/A",
    "explanation": json.loads(diag[11]) if diag[11] else [],
    "vitals": {
        "temperature": vitals[0] if vitals else "N/A",
        "heart_rate": vitals[1] if vitals else "N/A",
        "bp_systolic": vitals[2] if vitals else "N/A",
        "bp_diastolic": vitals[3] if vitals else "N/A",
        "respiratory_rate": vitals[4] if vitals else "N/A",
        "spo2": vitals[5] if vitals else "N/A",
    },
    "symptoms": symptoms,
    }


    file_path = f"reports/report_{diagnosis_id}.pdf"
    absolute_file_path = os.path.join(BASE_DIR, file_path)
    generate_pdf(report_data, absolute_file_path)

    # Save report path in DB
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM reports WHERE diagnosis_id=%s", (diagnosis_id,))
    existing = cur.fetchone()
    if existing:
        cur.execute("UPDATE reports SET file_path=%s WHERE diagnosis_id=%s", (file_path, diagnosis_id))
    else:
        cur.execute("""
            INSERT INTO reports (diagnosis_id,file_path)
            VALUES (%s,%s)
        """, (diagnosis_id, file_path))
    mysql.connection.commit()
    cur.close()

    return jsonify({
        "message": "PDF generated",
        "download_url": f"http://127.0.0.1:5000/{file_path}"
    })


@app.route("/api/reset-password", methods=["POST"])
def reset_password():
    data = request.json or {}
    email = data.get("email")
    new_password = data.get("password")

    if not email or not new_password:
        return jsonify({"error": "Email and password are required"}), 400

    if len(new_password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    hashed = hash_password(new_password).decode()
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE users SET password_hash=%s WHERE LOWER(email)=LOWER(%s)",
        (hashed, email),
    )
    mysql.connection.commit()

    if cur.rowcount == 0:
        cur.close()
        return jsonify({"error": "Email not found"}), 404

    cur.close()
    return jsonify({"message": "Password updated successfully"})

@app.route("/api/doctor/reports", methods=["GET"])
@role_required(["doctor"])
def doctor_reports():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT d.id, u.full_name, d.predicted_disease,
               d.confidence, d.risk_level, d.created_at
        FROM diagnosis_records d
        JOIN users u ON d.patient_id = u.id
        ORDER BY d.created_at DESC
    """)
    reports = cur.fetchall()
    cur.close()

    return jsonify({"reports": reports})

@app.route("/api/doctor/high-risk", methods=["GET"])
@role_required(["doctor"])
def high_risk_cases():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT d.id, u.full_name, d.predicted_disease,
               d.confidence, d.created_at
        FROM diagnosis_records d
        JOIN users u ON d.patient_id = u.id
        WHERE d.risk_level = 'High'
        ORDER BY d.created_at DESC
    """)
    cases = cur.fetchall()
    cur.close()

    return jsonify({"high_risk_cases": cases})

@app.route("/api/admin/all-records", methods=["GET"])
@role_required(["admin"])
def admin_all_records():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT d.id, u.full_name, d.predicted_disease,
               d.confidence, d.risk_level, d.created_at
        FROM diagnosis_records d
        JOIN users u ON d.patient_id = u.id
        ORDER BY d.created_at DESC
    """)
    records = cur.fetchall()
    cur.close()

    return jsonify({"records": records})

@app.route("/api/admin/users", methods=["GET"])
@role_required(["admin"])
def admin_users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, full_name, email, role, is_active FROM users")
    users = cur.fetchall()
    cur.close()

    return jsonify({"users": users})

@app.route("/api/admin/model-metrics", methods=["GET"])
@role_required(["admin"])
def admin_model_metrics():
    metrics = {}
    for disease, artifact in MODELS.items():
        metrics[disease] = artifact.get("metrics")
    return jsonify({"models": metrics})

@app.route("/api/admin/users/<int:user_id>/status", methods=["PUT"])
@role_required(["admin"])
def admin_update_user_status(user_id):
    data = request.json or {}
    if "is_active" not in data:
        return jsonify({"error": "is_active is required"}), 400

    is_active = 1 if bool(data.get("is_active")) else 0
    admin_id = request.user["user_id"]

    if user_id == admin_id:
        return jsonify({"error": "Admin cannot change own status"}), 400

    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET is_active=%s WHERE id=%s", (is_active, user_id))
    mysql.connection.commit()
    if cur.rowcount == 0:
        cur.close()
        return jsonify({"error": "User not found"}), 404
    cur.close()

    return jsonify({"message": "User status updated"})

@app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
@role_required(["admin"])
def admin_delete_user(user_id):
    admin_id = request.user["user_id"]
    if user_id == admin_id:
        return jsonify({"error": "Admin cannot delete own account"}), 400

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    mysql.connection.commit()
    if cur.rowcount == 0:
        cur.close()
        return jsonify({"error": "User not found"}), 404
    cur.close()

    return jsonify({"message": "User deleted"})

@app.route("/api/admin/report/<int:diagnosis_id>/pdf", methods=["DELETE"])
@role_required(["admin"])
def admin_delete_pdf(diagnosis_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT file_path FROM reports WHERE diagnosis_id=%s", (diagnosis_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        return jsonify({"error": "PDF report not found"}), 404

    file_path = row[0]
    absolute_file_path = os.path.join(BASE_DIR, file_path)

    cur.execute("DELETE FROM reports WHERE diagnosis_id=%s", (diagnosis_id,))
    mysql.connection.commit()
    cur.close()

    try:
        if os.path.exists(absolute_file_path):
            os.remove(absolute_file_path)
    except OSError:
        return jsonify({"error": "Failed to remove PDF file from disk"}), 500

    return jsonify({"message": "PDF deleted"})


@app.route('/reports/<path:filename>')
def download_file(filename):
    return send_from_directory(os.path.join(BASE_DIR, "reports"), filename)

@app.route("/")
def home():
    return "Smart Health Diagnosis API Running Successfully"


# =====================================================
# RUN SERVER
# =====================================================
if __name__ == "__main__":
    app.run(debug=True)

