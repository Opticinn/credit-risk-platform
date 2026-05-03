"""
Scoring Service — Penghubung antara model ML dan API

Cara kerja:
1. Terima data aplikasi kredit dari API
2. Preprocessing (sama persis dengan saat training)
3. Prediksi dengan XGBoost
4. Hitung SHAP values untuk explainability
5. Kembalikan hasil + penjelasan
"""

import joblib
import numpy as np
import shap
from pathlib import Path
from typing import Optional

# ─── Path ke model files ──────────────────────────────────────
MODEL_DIR = Path(__file__).parent.parent.parent.parent / "data" / "models"


class ScoringService:
    """
    Service ini di-load SEKALI saat server startup,
    lalu dipakai berulang kali untuk setiap request.
    
    Bayangkan seperti analis kredit yang sudah belajar bertahun-tahun
    (training), dan sekarang siap menilai aplikasi dalam hitungan detik.
    """

    def __init__(self):
        self.model = None
        self.explainer = None
        self.encoders = None
        self.feature_info = None
        self._loaded = False

    def load(self):
        """Load model dari disk ke memory."""
        if self._loaded:
            return

        print("🤖 Loading ML model...")
        self.model = joblib.load(MODEL_DIR / "xgboost_model.pkl")
        self.explainer = joblib.load(MODEL_DIR / "shap_explainer.pkl")
        self.encoders = joblib.load(MODEL_DIR / "label_encoders.pkl")
        self.feature_info = joblib.load(MODEL_DIR / "feature_info.pkl")
        self._loaded = True
        print("✅ ML model loaded!")

    def _preprocess(self, data: dict) -> np.ndarray:
        """
        Ubah data mentah dari API menjadi format yang bisa dibaca model.
        
        Harus IDENTIK dengan preprocessing saat training!
        Kalau beda, hasil prediksi akan kacau.
        """
        # Map field dari API ke field dataset
        # API pakai nama yang lebih user-friendly
        row = {
            "person_age": data["age"],
            "person_income": data["income"],
            "person_home_ownership": data.get("home_ownership", "RENT"),
            "person_emp_length": data.get("emp_length", 1.0),
            "loan_intent": data.get("loan_intent", "PERSONAL"),
            "loan_grade": data.get("loan_grade", "C"),
            "loan_amnt": data["loan_amount"],
            "loan_int_rate": data.get("interest_rate", 11.0),
            "loan_percent_income": data["loan_amount"] / data["income"],
            "cb_person_default_on_file": data.get("previous_default", "N"),
            "cb_person_cred_hist_length": data.get("credit_hist_length", 2),
        }

        # Encode kolom kategorikal — sama seperti saat training
        categorical_cols = self.feature_info["categorical_cols"]
        for col in categorical_cols:
            le = self.encoders[col]
            val = row[col]
            # Kalau nilai tidak dikenal, pakai nilai pertama sebagai default
            if val not in le.classes_:
                val = le.classes_[0]
            row[col] = le.transform([val])[0]

        # Susun features sesuai urutan saat training
        features = self.feature_info["features"]
        return np.array([[row[f] for f in features]])

    def predict(self, data: dict) -> dict:
        """
        Prediksi risiko kredit untuk satu aplikasi.
        
        Return:
        - probability_default: 0.0 - 1.0 (makin tinggi makin berisiko)
        - credit_score: 0 - 100 (kebalikan dari prob_default)
        - is_approved: True/False
        - shap_values: kontribusi setiap fitur
        - top_factors: faktor utama yang mempengaruhi keputusan
        """
        if not self._loaded:
            self.load()

        # Preprocessing
        X = self._preprocess(data)

        # Prediksi probabilitas default
        prob_default = float(self.model.predict_proba(X)[0][1])

        # Credit score: kebalikan dari prob_default, skala 0-100
        credit_score = round((1 - prob_default) * 100, 2)

        # Keputusan: approved kalau prob_default < 0.4
        is_approved = prob_default < 0.4

        # SHAP values — kontribusi setiap fitur ke keputusan
        shap_vals = self.explainer.shap_values(X)[0]
        features = self.feature_info["features"]

        shap_dict = {
            feat: round(float(val), 4)
            for feat, val in zip(features, shap_vals)
        }

        # Top 5 faktor paling berpengaruh
        sorted_shap = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)
        top_factors = []
        for feat, val in sorted_shap[:5]:
            top_factors.append({
                "factor": feat,
                "shap_value": val,
                "impact": "negative" if val > 0 else "positive",
                # SHAP positif = mendorong ke default (buruk)
                # SHAP negatif = mendorong ke aman (baik)
            })

        return {
            "probability_default": round(prob_default, 4),
            "credit_score": credit_score,
            "is_approved": is_approved,
            "shap_values": shap_dict,
            "top_factors": top_factors,
            "model_version": self.feature_info["model_version"],
        }


# ─── Singleton instance ───────────────────────────────────────
# Dibuat sekali, dipakai seluruh aplikasi
scoring_service = ScoringService()