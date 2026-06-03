CREATE DATABASE IF NOT EXISTS smarthealth;
USE smarthealth;

-- ===========================
-- USERS TABLE
-- ===========================

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('patient','doctor','admin') NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ===========================
-- PATIENT PROFILE EXTENSION
-- ===========================

CREATE TABLE patient_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    age INT,
    gender VARCHAR(50),
    blood_group VARCHAR(10),
    height FLOAT,
    weight FLOAT,
    bmi FLOAT,
    location VARCHAR(150),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ===========================
-- DIAGNOSIS RECORDS
-- ===========================

CREATE TABLE diagnosis_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    patient_display_name VARCHAR(150),
    disease_target VARCHAR(50) NOT NULL,
    predicted_disease VARCHAR(150),
    confidence FLOAT,
    risk_level ENUM('Low','Medium','High'),
    severity_level VARCHAR(50),
    duration_days INT,
    medical_history TEXT,
    smoking_status VARCHAR(50),
    alcohol_status VARCHAR(50),
    physical_activity VARCHAR(50),
    sleep_hours FLOAT,
    stress_level INT,
    patient_deleted BOOLEAN DEFAULT FALSE,
    ai_explanation TEXT,
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ===========================
-- SYMPTOMS TABLE
-- ===========================

CREATE TABLE symptoms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE
);

-- Preload symptoms
INSERT IGNORE INTO symptoms (name) VALUES
('fever'),
('cough'),
('chest_pain'),
('shortness_of_breath'),
('fatigue'),
('headache'),
('dizziness'),
('abdominal_pain'),
('joint_pain'),
('nausea'),
('weight_change');

-- ===========================
-- DIAGNOSIS_SYMPTOMS (Many-to-Many)
-- ===========================

CREATE TABLE diagnosis_symptoms (
    diagnosis_id INT,
    symptom_id INT,
    PRIMARY KEY (diagnosis_id, symptom_id),
    FOREIGN KEY (diagnosis_id) REFERENCES diagnosis_records(id) ON DELETE CASCADE,
    FOREIGN KEY (symptom_id) REFERENCES symptoms(id) ON DELETE CASCADE
);

-- ===========================
-- VITAL SIGNS TABLE
-- ===========================

CREATE TABLE vital_signs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    diagnosis_id INT,
    temperature FLOAT,
    heart_rate INT,
    bp_systolic INT,
    bp_diastolic INT,
    respiratory_rate INT,
    spo2 FLOAT,
    FOREIGN KEY (diagnosis_id) REFERENCES diagnosis_records(id) ON DELETE CASCADE
);

-- ===========================
-- DOCTOR SUGGESTIONS
-- ===========================

CREATE TABLE doctor_suggestions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    diagnosis_id INT,
    doctor_id INT,
    suggestion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (diagnosis_id) REFERENCES diagnosis_records(id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ===========================
-- PDF REPORTS STORAGE
-- ===========================

CREATE TABLE reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    diagnosis_id INT UNIQUE,
    file_path VARCHAR(255),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (diagnosis_id) REFERENCES diagnosis_records(id) ON DELETE CASCADE
);

-- ===========================
-- MODEL VERSION TRACKING
-- ===========================

CREATE TABLE ml_models (
    id INT AUTO_INCREMENT PRIMARY KEY,
    disease_type VARCHAR(50),
    model_name VARCHAR(100),
    version VARCHAR(50),
    accuracy FLOAT,
    trained_on DATE,
    is_active BOOLEAN DEFAULT TRUE
);

-- ===========================
-- SYSTEM AUDIT LOGS
-- ===========================

CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(255),
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
