"""
Agent Router — Endpoint untuk Multi-Agent Credit Decision

Endpoint:
- POST /agent/decide  → jalankan full multi-agent pipeline
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from app.models.user import User
from app.services.auth import get_current_user
from app.services.agents.graph import run_credit_decision

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────

class AgentDecisionRequest(BaseModel):
    age: int = Field(..., ge=18, le=100)
    income: float = Field(..., gt=0)
    home_ownership: str = Field("RENT")
    emp_length: float = Field(1.0, ge=0)
    loan_amount: float = Field(..., gt=0)
    loan_intent: str = Field("PERSONAL")
    loan_grade: str = Field("C")
    interest_rate: float = Field(11.0)
    credit_hist_length: int = Field(2, ge=0)
    previous_default: str = Field("N")

    class Config:
        json_schema_extra = {
            "example": {
                "age": 30,
                "income": 60000000,
                "home_ownership": "RENT",
                "emp_length": 5.0,
                "loan_amount": 10000000,
                "loan_intent": "PERSONAL",
                "loan_grade": "B",
                "interest_rate": 10.5,
                "credit_hist_length": 4,
                "previous_default": "N",
            }
        }


class AgentDecisionResponse(BaseModel):
    final_decision: str
    credit_score: Optional[float]
    probability_default: Optional[float]
    policy_compliant: Optional[bool]
    fraud_risk_level: Optional[str]
    fraud_flags: Optional[List[str]]
    risk_summary: Optional[str]
    final_explanation: str
    recommendation: str
    agent_logs: List[str]


# ─── Endpoint ─────────────────────────────────────────────────

@router.post("/decide", response_model=AgentDecisionResponse)
async def agent_decide(
    data: AgentDecisionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Jalankan full Multi-Agent Credit Decision Pipeline.

    4 agent bekerja secara berurutan:
    1. 🔍 Risk Analyst   → ML scoring + SHAP analysis
    2. 📋 Policy Checker → validasi kebijakan bank
    3. 🔎 Fraud Detector → deteksi anomali
    4. 📝 Report Writer  → keputusan final + penjelasan

    Lebih komprehensif dari endpoint /score/apply biasa
    karena melibatkan multiple perspective dalam keputusan.

    ⚠️  Lebih lambat (~30-60 detik) karena melibatkan LLM
    untuk setiap agent.
    """
    try:
        # Jalankan multi-agent pipeline
        result = run_credit_decision(
            application_data=data.model_dump(),
            application_id=None,
        )

        if result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=f"Agent error: {result['error']}"
            )

        return AgentDecisionResponse(
            final_decision=result.get("final_decision", "REVIEW"),
            credit_score=result.get("credit_score"),
            probability_default=result.get("probability_default"),
            policy_compliant=result.get("policy_compliant"),
            fraud_risk_level=result.get("fraud_risk_level"),
            fraud_flags=result.get("fraud_flags", []),
            risk_summary=result.get("risk_summary", ""),
            final_explanation=result.get("final_explanation", ""),
            recommendation=result.get("recommendation", ""),
            agent_logs=result.get("messages", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))