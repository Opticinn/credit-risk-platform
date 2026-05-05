"""
Agent State — Papan tulis bersama untuk semua agent

State ini dibagikan ke semua agent dalam graph.
Setiap agent bisa baca state dari agent sebelumnya
dan tulis hasilnya untuk agent berikutnya.

Analogi: seperti formulir yang diisi bergantian oleh
beberapa departemen — setiap departemen mengisi bagiannya
dan meneruskan ke departemen berikutnya.
"""

from typing import TypedDict, Optional, List


class CreditDecisionState(TypedDict):
    """
    State yang dibagikan ke semua agent.
    
    TypedDict = dictionary dengan tipe data yang jelas.
    Ini memastikan setiap agent tahu persis data apa yang tersedia.
    """

    # ─── Input dari user ──────────────────────────────────────
    application_data: dict          # data aplikasi nasabah
    application_id: Optional[str]   # ID aplikasi di database

    # ─── Hasil Risk Analyst Agent ─────────────────────────────
    credit_score: Optional[float]           # 0-100
    probability_default: Optional[float]    # 0.0-1.0
    is_approved_by_model: Optional[bool]    # keputusan model ML
    shap_factors: Optional[List[dict]]      # top factors dari SHAP
    risk_summary: Optional[str]             # ringkasan risiko

    # ─── Hasil Policy Checker Agent ───────────────────────────
    policy_compliant: Optional[bool]        # apakah memenuhi kebijakan?
    policy_notes: Optional[str]             # catatan kebijakan
    relevant_policies: Optional[List[str]]  # kebijakan yang relevan

    # ─── Hasil Fraud Detector Agent ───────────────────────────
    fraud_flags: Optional[List[str]]        # flag anomali yang ditemukan
    fraud_risk_level: Optional[str]         # LOW / MEDIUM / HIGH
    fraud_notes: Optional[str]              # penjelasan fraud check

    # ─── Hasil Report Writer Agent ────────────────────────────
    final_decision: Optional[str]           # APPROVED / REJECTED / REVIEW
    final_explanation: Optional[str]        # penjelasan lengkap untuk nasabah
    recommendation: Optional[str]           # saran untuk nasabah

    # ─── Metadata ─────────────────────────────────────────────
    messages: List[str]                     # log semua langkah agent
    error: Optional[str]                    # error jika ada