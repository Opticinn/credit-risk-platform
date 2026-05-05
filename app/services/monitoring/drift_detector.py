"""
Drift Detector — Deteksi perubahan distribusi data (Model Drift)

Menggunakan Evidently AI untuk membandingkan:
- Reference data: data yang dipakai saat training
- Current data: data aplikasi kredit terbaru

Kalau distribusinya berbeda jauh → drift terdeteksi → alert!

Analogi: seperti dokter yang cek tekanan darah pasien secara rutin.
Kalau ada perubahan signifikan → segera ditangani sebelum jadi masalah besar.
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from app.services.monitoring.alerting import alerting_service

# ─── Path ────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
MODEL_DIR = DATA_DIR / "models"
REPORTS_DIR = DATA_DIR / "drift_reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Threshold — seberapa besar perbedaan sebelum dianggap drift
DRIFT_THRESHOLD = 0.15


class DriftDetector:
    """
    Mendeteksi model drift dengan membandingkan distribusi data.
    
    Cara kerja:
    1. Load reference data (data training asli)
    2. Load current data (data aplikasi terbaru dari DB)
    3. Bandingkan distribusi setiap feature
    4. Kalau ada yang drift → kirim alert Telegram
    """

    def __init__(self):
        self.reference_data = None
        self._loaded = False

    def load_reference(self):
        """Load data training sebagai baseline referensi."""
        if self._loaded:
            return

        ref_path = DATA_DIR / "credit_risk_dataset.csv"
        if not ref_path.exists():
            print("⚠️  Reference data tidak ditemukan")
            return

        df = pd.read_csv(ref_path)

        # Preprocessing sama seperti saat training
        df["person_emp_length"] = df["person_emp_length"].fillna(df["person_emp_length"].median())
        df["loan_int_rate"] = df["loan_int_rate"].fillna(df["loan_int_rate"].median())
        df = df[df["person_age"] <= 100]
        df = df[df["person_emp_length"] <= 60]

        # Ambil sample 1000 baris sebagai referensi
        self.reference_data = df.sample(min(1000, len(df)), random_state=42)
        self._loaded = True
        print(f"✅ Reference data loaded: {len(self.reference_data)} rows")

    def _calculate_psi(self, expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
        """
        PSI = Population Stability Index
        
        Ini adalah cara mengukur seberapa besar perubahan distribusi data.
        
        Skala PSI:
        - PSI < 0.1  → tidak ada drift (aman)
        - PSI 0.1-0.2 → drift ringan (perhatikan)
        - PSI > 0.2  → drift signifikan (perlu action!)
        
        Analogi: seperti mengukur seberapa berbeda populasi nasabah
        hari ini vs saat model ditraining.
        """
        # Buat histogram
        breakpoints = np.linspace(
            min(expected.min(), actual.min()),
            max(expected.max(), actual.max()),
            bins + 1
        )

        expected_pct = np.histogram(expected, bins=breakpoints)[0] / len(expected)
        actual_pct = np.histogram(actual, bins=breakpoints)[0] / len(actual)

        # Hindari division by zero
        expected_pct = np.where(expected_pct == 0, 0.0001, expected_pct)
        actual_pct = np.where(actual_pct == 0, 0.0001, actual_pct)

        psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
        return float(psi)

    def detect(self, current_data: pd.DataFrame) -> dict:
        """
        Bandingkan current data dengan reference data.
        
        Return dict berisi:
        - drift_detected: True/False
        - features: PSI score per feature
        - drifted_features: list feature yang drift
        """
        if not self._loaded:
            self.load_reference()

        if self.reference_data is None or current_data is None or len(current_data) < 10:
            return {"drift_detected": False, "reason": "Data tidak cukup untuk analisis"}

        # Feature numerik yang kita monitor
        numeric_features = [
            "person_age",
            "person_income",
            "loan_amnt",
            "loan_int_rate",
            "loan_percent_income",
            "cb_person_cred_hist_length",
        ]

        results = {}
        drifted = []

        for feature in numeric_features:
            if feature not in self.reference_data.columns:
                continue
            if feature not in current_data.columns:
                continue

            ref_vals = self.reference_data[feature].dropna().values
            cur_vals = current_data[feature].dropna().values

            if len(cur_vals) < 5:
                continue

            psi = self._calculate_psi(ref_vals, cur_vals)
            results[feature] = round(psi, 4)

            if psi > DRIFT_THRESHOLD:
                drifted.append(feature)
                # Kirim alert untuk setiap feature yang drift
                alerting_service.send_drift_alert(feature, psi, DRIFT_THRESHOLD)

        drift_detected = len(drifted) > 0

        report = {
            "drift_detected": drift_detected,
            "checked_at": datetime.now().isoformat(),
            "total_current_samples": len(current_data),
            "features": results,
            "drifted_features": drifted,
            "threshold": DRIFT_THRESHOLD,
        }

        # Simpan report ke file
        report_path = REPORTS_DIR / f"drift_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        import json
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return report


# ─── Singleton ────────────────────────────────────────────────
drift_detector = DriftDetector()