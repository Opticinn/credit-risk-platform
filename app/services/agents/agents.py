"""
Credit Decision Agents — 4 agent spesialis

Setiap agent punya tugas spesifik:
1. Risk Analyst   → scoring + SHAP analysis
2. Policy Checker → validasi kebijakan bank
3. Fraud Detector → deteksi anomali
4. Report Writer  → buat laporan final

Analogi: seperti tim analis di bank sungguhan,
masing-masing punya keahlian berbeda tapi bekerja
untuk satu keputusan yang sama.
"""

import httpx
from app.services.agents.state import CreditDecisionState
from app.services.ml.scoring import scoring_service
from app.services.rag.rag_service import rag_service


# ─── Helper: Panggil Qwen2.5 via Ollama ───────────────────────
def call_llm(prompt: str, max_tokens: int = 512) -> str:
    try:
        with httpx.Client(timeout=120.0) as client:
            res = client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5:7b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": max_tokens,
                    }
                }
            )
            res.raise_for_status()
            data = res.json()
            return data.get("response", "").strip()

    except httpx.ConnectError:
        return "Layanan AI sedang tidak tersedia."
    except httpx.TimeoutException:
        return "Layanan AI timeout — coba lagi."
    except Exception as e:
        return f"AI error: {str(e)[:100]}"


# ══════════════════════════════════════════════════════════════
# AGENT 1 — Risk Analyst
# Tugas: jalankan ML model, analisis SHAP, buat ringkasan risiko
# ══════════════════════════════════════════════════════════════
def risk_analyst_agent(state: CreditDecisionState) -> CreditDecisionState:
    """
    Risk Analyst Agent.
    
    Seperti analis kredit yang menghitung angka-angka:
    - Credit score berapa?
    - Probabilitas gagal bayar berapa?
    - Faktor apa yang paling berpengaruh?
    """
    print("🔍 Risk Analyst Agent: Analyzing credit risk...")
    messages = state.get("messages", [])
    messages.append("Risk Analyst: Memulai analisis risiko kredit...")

    try:
        # Jalankan ML model scoring
        app_data = state["application_data"]
        result = scoring_service.predict(app_data)

        credit_score = result["credit_score"]
        prob_default = result["probability_default"]
        is_approved = result["is_approved"]
        top_factors = result["top_factors"]

        # Format faktor untuk ringkasan
        factors_text = ""
        for f in top_factors[:3]:
            impact = "✅ positif" if f["impact"] == "positive" else "⚠️ negatif"
            factors_text += f"  - {f['factor']}: {impact}\n"

        # Minta LLM buat ringkasan risiko
        prompt = f"""Kamu adalah analis risiko kredit profesional.
Berikan ringkasan singkat risiko kredit dalam 2 kalimat Bahasa Indonesia.

Data:
- Credit Score: {credit_score:.1f}/100
- Probabilitas gagal bayar: {prob_default*100:.1f}%
- Status: {"DISETUJUI" if is_approved else "DITOLAK"}
- Faktor utama:
{factors_text}

Ringkasan risiko (2 kalimat):"""

        risk_summary = call_llm(prompt, max_tokens=150)

        messages.append(f"Risk Analyst: Score={credit_score:.1f}, PD={prob_default*100:.1f}%, {'APPROVE' if is_approved else 'REJECT'}")

        return {
            **state,
            "credit_score": credit_score,
            "probability_default": prob_default,
            "is_approved_by_model": is_approved,
            "shap_factors": top_factors,
            "risk_summary": risk_summary,
            "messages": messages,
        }

    except Exception as e:
        messages.append(f"Risk Analyst Error: {str(e)}")
        return {**state, "messages": messages, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# AGENT 2 — Policy Checker
# Tugas: cek apakah aplikasi memenuhi kebijakan bank
# ══════════════════════════════════════════════════════════════
def policy_checker_agent(state: CreditDecisionState) -> CreditDecisionState:
    """
    Policy Checker Agent.
    
    Seperti compliance officer yang cek apakah
    aplikasi memenuhi semua persyaratan regulasi dan kebijakan bank.
    Menggunakan RAG untuk cari kebijakan yang relevan.
    """
    print("📋 Policy Checker Agent: Checking policy compliance...")
    messages = state.get("messages", [])
    messages.append("Policy Checker: Memeriksa kesesuaian kebijakan...")

    try:
        app_data = state["application_data"]
        credit_score = state.get("credit_score", 50)
        prob_default = state.get("probability_default", 0.5)

        # Hitung DTI dan LTI
        income = app_data.get("income", 1)
        loan_amount = app_data.get("loan_amount", 0)
        lti = loan_amount / income if income > 0 else 999

        # Cari kebijakan relevan dari ChromaDB
        query = f"persyaratan kredit grade {app_data.get('loan_grade', 'C')} income ratio"
        relevant_policies = rag_service.retrieve(query, n_results=2)

        # Cek compliance rules
        flags = []
        if app_data.get("age", 0) < 18:
            flags.append("❌ Usia di bawah minimum (18 tahun)")
        if lti > 0.5:
            flags.append(f"⚠️ LTI terlalu tinggi: {lti*100:.1f}% (maks 50%)")
        if app_data.get("previous_default") == "Y":
            flags.append("⚠️ Riwayat default sebelumnya")
        if credit_score < 30:
            flags.append("❌ Credit score terlalu rendah")

        policy_compliant = len([f for f in flags if f.startswith("❌")]) == 0

        # Minta LLM buat catatan kebijakan
        prompt = f"""Kamu adalah compliance officer bank.
Berikan catatan kebijakan singkat dalam 2 kalimat Bahasa Indonesia.

Aplikasi:
- Grade: {app_data.get('loan_grade', 'C')}
- LTI Ratio: {lti*100:.1f}%
- Riwayat default: {app_data.get('previous_default', 'N')}
- Flag: {', '.join(flags) if flags else 'Tidak ada'}
- Status compliance: {"SESUAI" if policy_compliant else "TIDAK SESUAI"}

Catatan kebijakan (2 kalimat):"""

        policy_notes = call_llm(prompt, max_tokens=150)

        messages.append(f"Policy Checker: Compliant={policy_compliant}, Flags={len(flags)}")

        return {
            **state,
            "policy_compliant": policy_compliant,
            "policy_notes": policy_notes,
            "relevant_policies": relevant_policies,
            "messages": messages,
        }

    except Exception as e:
        messages.append(f"Policy Checker Error: {str(e)}")
        return {**state, "messages": messages, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# AGENT 3 — Fraud Detector
# Tugas: deteksi anomali dan tanda-tanda penipuan
# ══════════════════════════════════════════════════════════════
def fraud_detector_agent(state: CreditDecisionState) -> CreditDecisionState:
    """
    Fraud Detector Agent.
    
    Seperti investigator yang mencari tanda-tanda penipuan:
    - Income tidak realistis?
    - Pinjaman terlalu besar dibanding income?
    - Umur tidak wajar?
    """
    print("🔎 Fraud Detector Agent: Checking for anomalies...")
    messages = state.get("messages", [])
    messages.append("Fraud Detector: Memeriksa anomali dan indikasi fraud...")

    try:
        app_data = state["application_data"]
        fraud_flags = []

        age = app_data.get("age", 30)
        income = app_data.get("income", 1)
        loan_amount = app_data.get("loan_amount", 0)
        emp_length = app_data.get("emp_length", 0)

        # Rule-based fraud detection
        # Rule 1: Income tidak realistis
        if income > 5_000_000_000:  # > 5 miliar per tahun
            fraud_flags.append("Income sangat tidak realistis (> Rp 5 miliar/tahun)")

        # Rule 2: Umur vs lama kerja tidak masuk akal
        if age < 22 and emp_length > 5:
            fraud_flags.append(f"Umur {age} tahun tapi sudah kerja {emp_length} tahun — tidak konsisten")

        # Rule 3: Pinjaman sangat besar dibanding income
        if loan_amount > income * 50:
            fraud_flags.append(f"Pinjaman {loan_amount/income:.0f}x income — sangat tidak wajar")

        # Rule 4: Income sangat rendah tapi pinjaman besar
        if income < 10_000_000 and loan_amount > 100_000_000:
            fraud_flags.append("Income sangat rendah tapi pinjaman sangat besar")

        # Tentukan risk level
        if len(fraud_flags) == 0:
            fraud_risk_level = "LOW"
        elif len(fraud_flags) == 1:
            fraud_risk_level = "MEDIUM"
        else:
            fraud_risk_level = "HIGH"

        # Minta LLM buat catatan
        prompt = f"""Kamu adalah fraud analyst bank.
Berikan catatan fraud check singkat dalam 1-2 kalimat Bahasa Indonesia.

Hasil pemeriksaan:
- Risk level: {fraud_risk_level}
- Flag ditemukan: {len(fraud_flags)}
- Detail: {', '.join(fraud_flags) if fraud_flags else 'Tidak ada anomali'}

Catatan fraud check:"""

        fraud_notes = call_llm(prompt, max_tokens=100)

        messages.append(f"Fraud Detector: Level={fraud_risk_level}, Flags={len(fraud_flags)}")

        return {
            **state,
            "fraud_flags": fraud_flags,
            "fraud_risk_level": fraud_risk_level,
            "fraud_notes": fraud_notes,
            "messages": messages,
        }

    except Exception as e:
        messages.append(f"Fraud Detector Error: {str(e)}")
        return {**state, "messages": messages, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# AGENT 4 — Report Writer
# Tugas: gabungkan semua hasil, buat keputusan final + penjelasan
# ══════════════════════════════════════════════════════════════
def report_writer_agent(state: CreditDecisionState) -> CreditDecisionState:
    """
    Report Writer Agent.
    
    Seperti manajer kredit senior yang membaca semua laporan
    dari tim analis, lalu membuat keputusan final dan
    menulis penjelasan yang mudah dipahami nasabah.
    """
    print("📝 Report Writer Agent: Writing final report...")
    messages = state.get("messages", [])
    messages.append("Report Writer: Menyusun laporan dan keputusan final...")

    try:
        # Kumpulkan semua hasil dari agent sebelumnya
        credit_score = state.get("credit_score", 0)
        prob_default = state.get("probability_default", 1)
        is_approved_model = state.get("is_approved_by_model", False)
        policy_compliant = state.get("policy_compliant", False)
        fraud_risk = state.get("fraud_risk_level", "LOW")
        fraud_flags = state.get("fraud_flags", [])
        risk_summary = state.get("risk_summary", "")
        policy_notes = state.get("policy_notes", "")
        fraud_notes = state.get("fraud_notes", "")
        app_data = state["application_data"]

        # ─── Logika Keputusan Final ────────────────────────────
        # Keputusan berdasarkan kombinasi semua agent:

        if fraud_risk == "HIGH":
            # Fraud risk tinggi → langsung REVIEW manual
            final_decision = "REVIEW"
        elif not policy_compliant:
            # Tidak comply dengan kebijakan → REJECTED
            final_decision = "REJECTED"
        elif is_approved_model and fraud_risk == "LOW":
            # Model approve + tidak ada fraud → APPROVED
            final_decision = "APPROVED"
        elif is_approved_model and fraud_risk == "MEDIUM":
            # Model approve tapi ada sedikit flag → REVIEW
            final_decision = "REVIEW"
        else:
            # Model reject → REJECTED
            final_decision = "REJECTED"

        # ─── Generate Penjelasan dengan LLM ───────────────────
        prompt = f"""Kamu adalah manajer kredit senior di bank Indonesia.
Tulis penjelasan keputusan kredit yang ramah dan profesional dalam Bahasa Indonesia.

## Ringkasan Analisis Tim:
- Credit Score: {credit_score:.1f}/100
- Probabilitas Gagal Bayar: {prob_default*100:.1f}%
- Analisis Risiko: {risk_summary}
- Status Kebijakan: {"Sesuai" if policy_compliant else "Ada masalah kebijakan"}
- Catatan Kebijakan: {policy_notes}
- Fraud Check: Level {fraud_risk} — {fraud_notes}

## Keputusan Final: {final_decision}

## Data Nasabah:
- Usia: {app_data.get('age')} tahun
- Income: Rp {app_data.get('income', 0):,}/tahun
- Pinjaman: Rp {app_data.get('loan_amount', 0):,}
- Tujuan: {app_data.get('loan_intent', 'PERSONAL')}

Tulis penjelasan untuk nasabah (3 paragraf):
1. Keputusan dan alasan utama
2. Faktor-faktor yang mempengaruhi
3. Saran ke depan (jika ditolak) atau selamat (jika disetujui)

Penjelasan:"""

        final_explanation = call_llm(prompt, max_tokens=400)

        # Generate rekomendasi singkat
        if final_decision == "APPROVED":
            recommendation = "Selamat! Pengajuan Anda disetujui. Silakan lengkapi dokumen untuk pencairan."
        elif final_decision == "REJECTED":
            recommendation = "Pengajuan ditolak. Tingkatkan credit score dan kurangi rasio hutang sebelum mengajukan kembali."
        else:
            recommendation = "Pengajuan memerlukan review manual oleh tim analis kami. Kami akan menghubungi dalam 3 hari kerja."

        messages.append(f"Report Writer: Keputusan final = {final_decision}")

        return {
            **state,
            "final_decision": final_decision,
            "final_explanation": final_explanation,
            "recommendation": recommendation,
            "messages": messages,
        }

    except Exception as e:
        messages.append(f"Report Writer Error: {str(e)}")
        return {**state, "messages": messages, "error": str(e)}