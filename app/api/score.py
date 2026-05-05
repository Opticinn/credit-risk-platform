"""
Score Router — Endpoint untuk submit & scoring aplikasi kredit

Endpoint:
- POST /score/apply     → submit aplikasi, langsung dapat hasil scoring
- GET  /score/{id}      → lihat hasil scoring aplikasi tertentu
- GET  /score/history   → riwayat semua aplikasi milik user
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
import uuid

from app.database import get_db
from app.models.user import User
from app.models.application import CreditApplication, ApplicationStatus
from app.models.score import CreditScore
from app.services.auth import get_current_user
from app.services.ml.scoring import scoring_service

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────

class ApplicationRequest(BaseModel):
    """Data yang dikirim pemohon kredit."""

    # Data pribadi
    age: int = Field(..., ge=18, le=100, description="Umur pemohon")
    income: float = Field(..., gt=0, description="Pendapatan tahunan (Rp)")
    home_ownership: str = Field("RENT", description="RENT / OWN / MORTGAGE / OTHER")
    emp_length: float = Field(1.0, ge=0, description="Lama bekerja (tahun)")

    # Data pinjaman
    loan_amount: float = Field(..., gt=0, description="Jumlah pinjaman (Rp)")
    loan_intent: str = Field("PERSONAL", description="Tujuan pinjaman")
    loan_grade: str = Field("C", description="Grade pinjaman: A-G")
    interest_rate: float = Field(11.0, gt=0, description="Suku bunga (%)")

    # Riwayat kredit
    previous_default: str = Field("N", description="Pernah default? Y/N")
    credit_hist_length: int = Field(2, ge=0, description="Lama riwayat kredit (tahun)")

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
                "previous_default": "N",
                "credit_hist_length": 4,
            }
        }


class TopFactor(BaseModel):
    factor: str
    shap_value: float
    impact: str


class ScoreResponse(BaseModel):
    """Hasil scoring yang dikembalikan ke client."""
    application_id: str
    credit_score: float
    probability_default: float
    is_approved: bool
    status: str
    top_factors: List[TopFactor]
    model_version: str


# ─── Endpoints ────────────────────────────────────────────────

@router.post("/apply", response_model=ScoreResponse, status_code=201)
async def apply_credit(
    data: ApplicationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit aplikasi kredit dan langsung dapat hasil scoring.

    Cara kerja:
    1. Simpan data aplikasi ke database
    2. Kirim ke ML model untuk di-scoring
    3. Simpan hasil scoring
    4. Kembalikan hasil ke user
    """

    # Step 1 — Simpan aplikasi
    application = CreditApplication(
        applicant_id=current_user.id,
        age=data.age,
        income=data.income,
        loan_amount=data.loan_amount,
        loan_tenure_months=12,
        employment_type=data.loan_intent,     
        existing_debt=0,
        credit_history_score=min(850, max(300, data.credit_hist_length * 60 + 300)),
        num_dependents=0,
        status=ApplicationStatus.processing,
    )
    db.add(application)
    await db.flush()

    # Step 2 — Scoring dengan ML model
    try:
        result = scoring_service.predict(data.model_dump())
    except Exception as e:
        application.status = ApplicationStatus.pending
        raise HTTPException(status_code=500, detail=f"Scoring error: {str(e)}")

    # Step 3 — Simpan hasil scoring
    score = CreditScore(
        application_id=application.id,
        probability_default=result["probability_default"],
        credit_score=result["credit_score"],
        is_approved=result["is_approved"],
        shap_values=result["shap_values"],
        top_factors=result["top_factors"],
        model_version=result["model_version"],
    )
    db.add(score)

    # Update status aplikasi
    application.status = (
        ApplicationStatus.approved if result["is_approved"]
        else ApplicationStatus.rejected
    )
    await db.flush()

    return ScoreResponse(
        application_id=str(application.id),
        credit_score=result["credit_score"],
        probability_default=result["probability_default"],
        is_approved=result["is_approved"],
        status=application.status.value,
        top_factors=[TopFactor(**f) for f in result["top_factors"]],
        model_version=result["model_version"],
    )


@router.get("/history", response_model=List[ScoreResponse])
async def get_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lihat riwayat semua aplikasi kredit milik user yang sedang login."""

    result = await db.execute(
        select(CreditApplication, CreditScore)
        .join(CreditScore, CreditScore.application_id == CreditApplication.id, isouter=True)
        .where(CreditApplication.applicant_id == current_user.id)
        .order_by(CreditApplication.created_at.desc())
    )
    rows = result.all()

    if not rows:
        return []

    responses = []
    for app, score in rows:
        if score:
            responses.append(ScoreResponse(
                application_id=str(app.id),
                credit_score=score.credit_score,
                probability_default=score.probability_default,
                is_approved=score.is_approved,
                status=app.status.value,
                top_factors=[TopFactor(**f) for f in (score.top_factors or [])],
                model_version=score.model_version or "v1.0",
            ))

    return responses


@router.get("/{application_id}", response_model=ScoreResponse)
async def get_score(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lihat hasil scoring satu aplikasi berdasarkan ID."""

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
    return ScoreResponse(
        application_id=str(app.id),
        credit_score=score.credit_score,
        probability_default=score.probability_default,
        is_approved=score.is_approved,
        status=app.status.value,
        top_factors=[TopFactor(**f) for f in (score.top_factors or [])],
        model_version=score.model_version or "v1.0",
    )