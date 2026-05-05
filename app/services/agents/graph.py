"""
Credit Decision Graph — Orkestrasi Multi-Agent dengan LangGraph

LangGraph mengatur alur kerja agent seperti flowchart:

START
  ↓
risk_analyst     → scoring + SHAP
  ↓
policy_checker   → validasi kebijakan
  ↓
fraud_detector   → deteksi anomali
  ↓
report_writer    → laporan final
  ↓
END

Kenapa pakai LangGraph?
- Alur yang jelas dan dapat di-debug
- State dibagikan otomatis antar agent
- Mudah ditambah/ubah agent
- Production-ready
"""

from langgraph.graph import StateGraph, END
from app.services.agents.state import CreditDecisionState
from app.services.agents.agents import (
    risk_analyst_agent,
    policy_checker_agent,
    fraud_detector_agent,
    report_writer_agent,
)


def build_credit_decision_graph():
    """
    Bangun graph multi-agent untuk credit decision.
    
    StateGraph = graph yang punya state bersama.
    Setiap node = satu agent.
    Setiap edge = alur dari satu agent ke agent berikutnya.
    """

    # Buat graph dengan state CreditDecisionState
    graph = StateGraph(CreditDecisionState)

    # ─── Tambahkan nodes (agent) ───────────────────────────────
    # Setiap node punya nama dan fungsi agent-nya
    graph.add_node("risk_analyst", risk_analyst_agent)
    graph.add_node("policy_checker", policy_checker_agent)
    graph.add_node("fraud_detector", fraud_detector_agent)
    graph.add_node("report_writer", report_writer_agent)

    # ─── Tentukan alur (edges) ─────────────────────────────────
    # START → risk_analyst (agent pertama yang dipanggil)
    graph.set_entry_point("risk_analyst")

    # risk_analyst → policy_checker
    graph.add_edge("risk_analyst", "policy_checker")

    # policy_checker → fraud_detector
    graph.add_edge("policy_checker", "fraud_detector")

    # fraud_detector → report_writer
    graph.add_edge("fraud_detector", "report_writer")

    # report_writer → END (selesai)
    graph.add_edge("report_writer", END)

    # Compile graph menjadi runnable
    return graph.compile()


# ─── Singleton — build sekali, pakai berkali-kali ─────────────
credit_graph = build_credit_decision_graph()


def run_credit_decision(application_data: dict, application_id: str = None) -> dict:
    """
    Jalankan seluruh pipeline multi-agent untuk satu aplikasi kredit.
    
    Args:
        application_data: data aplikasi dari API
        application_id: ID aplikasi di database (opsional)
    
    Returns:
        State akhir berisi semua hasil dari semua agent
    """
    # Initial state — hanya isi input, sisanya None
    initial_state: CreditDecisionState = {
        "application_data": application_data,
        "application_id": application_id,
        "credit_score": None,
        "probability_default": None,
        "is_approved_by_model": None,
        "shap_factors": None,
        "risk_summary": None,
        "policy_compliant": None,
        "policy_notes": None,
        "relevant_policies": None,
        "fraud_flags": None,
        "fraud_risk_level": None,
        "fraud_notes": None,
        "final_decision": None,
        "final_explanation": None,
        "recommendation": None,
        "messages": [],
        "error": None,
    }

    # Jalankan graph — LangGraph otomatis eksekusi setiap agent berurutan
    final_state = credit_graph.invoke(initial_state)
    return final_state