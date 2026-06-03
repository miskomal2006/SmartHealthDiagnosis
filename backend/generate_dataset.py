import pandas as pd
import numpy as np
import os

np.random.seed(42)

SYMPTOMS = [
    "fever","cough","chest_pain","shortness_of_breath",
    "fatigue","headache","dizziness","abdominal_pain",
    "joint_pain","nausea","weight_change"
]

def generate_data(disease_name, rows=1000):
    data = []

    for _ in range(rows):

        age = np.random.randint(18, 85)
        bmi = np.random.uniform(18, 40)
        temperature = np.random.uniform(36, 40)
        heart_rate = np.random.randint(60, 120)
        bp_sys = np.random.randint(100, 180)
        bp_dia = np.random.randint(60, 120)
        spo2 = np.random.uniform(85, 100)

        symptoms = np.random.randint(0, 2, len(SYMPTOMS))

        # Disease logic (synthetic risk rule)
        risk_score = (
            (bmi > 30) +
            (bp_sys > 150) +
            (heart_rate > 100) +
            (spo2 < 92) +
            sum(symptoms)
        )

        target = 1 if risk_score > 5 else 0

        row = [
            age,bmi,temperature,heart_rate,
            bp_sys,bp_dia,spo2
        ] + list(symptoms) + [target]

        data.append(row)

    columns = [
        "age","bmi","temperature","heart_rate",
        "bp_systolic","bp_diastolic","spo2"
    ] + SYMPTOMS + ["target"]

    df = pd.DataFrame(data, columns=columns)

    os.makedirs("../dataset", exist_ok=True)
    df.to_csv(f"../dataset/{disease_name}.csv", index=False)

    print(f"{disease_name}.csv generated with {rows} rows")


if __name__ == "__main__":
    diseases = ["diabetes","heart","respiratory","kidney","liver","cancer"]

    for d in diseases:
        generate_data(d, rows=1000)
