"""
Chat Router — Endpoint AI Chat dengan Qwen2.5 + RAG

Endpoint:
- POST /chat/explain/{application_id}  → minta penjelasan keputusan kredit
- POST /chat/ask                        → tanya bebas seputar kredit
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.application import CreditApplication
from app.models.score import CreditScore
from app.services.auth import get_current_user
from app.services.rag.rag_service import rag_service

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    question: Optional[str] = None


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    application_id: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────

@router.post("/explain/{application_id}", response_model=ChatResponse)
async def explain_decision(
    application_id: str,
    body: ExplainRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Minta penjelasan keputusan kredit dalam bahasa natural.

    Qwen2.5 akan menjelaskan kenapa disetujui/ditolak berdasarkan:
    - Data aplikasi nasabah
    - Hasil SHAP dari model XGBoost
    - Referensi kebijakan kredit bank (dari ChromaDB)

    Contoh pertanyaan:
    - "Kenapa saya ditolak?"
    - "Faktor apa yang paling berpengaruh?"
    - "Apa yang harus saya lakukan agar disetujui?"
    """
    result = await db.execute(
        select(CreditApplication, CreditScore)
        .join(CreditScore, CreditScore.application_id == CreditApplication.id)
        .where(CreditApplication.id == application_id)
        .where(CreditApplication.applicant_id == current_user.id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Aplikasi tidak ditemukan")

    app, score = row

    application_data = {
        "age": app.age,
        "income": app.income,
        "loan_amount": app.loan_amount,
        "home_ownership": "RENT",
        "emp_length": 1.0,
        "loan_intent": app.employment_type,   
        "loan_grade": "C",
        "previous_default": "N",
    }

    score_result = {
        "credit_score": score.credit_score,
        "probability_default": score.probability_default,
        "is_approved": score.is_approved,
        "top_factors": score.top_factors or [],
    }

    try:
        answer = rag_service.explain_decision(
            application_data=application_data,
            score_result=score_result,
            question=body.question,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")

    return ChatResponse(answer=answer, application_id=application_id)


@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Tanya bebas seputar kredit — Qwen2.5 akan jawab berdasarkan
    kebijakan bank kita (RAG).

    Contoh pertanyaan:
    - "Apa itu DTI ratio?"
    - "Bagaimana cara meningkatkan credit score saya?"
    - "Apa perbedaan grade A dan grade B?"
    """
    try:
        answer = rag_service.ask_question(body.question)
        return ChatResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")