"""
Officer Router — Endpoint khusus untuk Loan Officer & Admin

Endpoint:
- GET  /officer/applications          → lihat semua aplikasi
- GET  /officer/applications/{id}     → lihat detail satu aplikasi
- PUT  /officer/applications/{id}     → update status (approve/reject manual)
- GET  /officer/stats                 → statistik dashboard
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.application import CreditApplication, ApplicationStatus
from app.models.score import CreditScore
from app.services.auth import get_current_loan_officer

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────

class ApplicationSummary(BaseModel):
    application_id: str
    applicant_name: str
    applicant_email: str
    age: int
    income: float
    loan_amount: float
    status: str
    credit_score: Optional[float] = None
    is_approved: Optional[bool] = None
    created_at: str


class DashboardStats(BaseModel):
    total: int
    approved: int
    rejected: int
    pending: int
    avg_credit_score: float
    approval_rate: float


class UpdateStatusRequest(BaseModel):
    status: str
    rejection_reason: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────

@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_loan_officer),
):
    """
    Statistik untuk dashboard loan officer.
    Menghitung total aplikasi, approval rate, dan rata-rata credit score.
    """
    # Hitung per status
    result = await db.execute(
        select(CreditApplication.status, func.count(CreditApplication.id))
        .group_by(CreditApplication.status)
    )
    status_counts = dict(result.all())

    total = sum(status_counts.values())
    approved = status_counts.get(ApplicationStatus.approved, 0)
    rejected = status_counts.get(ApplicationStatus.rejected, 0)
    pending = status_counts.get(ApplicationStatus.pending, 0) + \
              status_counts.get(ApplicationStatus.processing, 0)

    # Rata-rata credit score
    score_result = await db.execute(
        select(func.avg(CreditScore.credit_score))
    )
    avg_score = score_result.scalar() or 0.0

    return DashboardStats(
        total=total,
        approved=approved,
        rejected=rejected,
        pending=pending,
        avg_credit_score=round(float(avg_score), 1),
        approval_rate=round(approved / total * 100, 1) if total > 0 else 0.0,
    )


@router.get("/applications", response_model=List[ApplicationSummary])
async def get_all_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_loan_officer),
    status: Optional[str] = None,
    limit: int = 50,
):
    """
    Ambil semua aplikasi kredit — khusus loan officer & admin.
    Bisa difilter berdasarkan status.
    """
    query = (
        select(CreditApplication, User, CreditScore)
        .join(User, User.id == CreditApplication.applicant_id)
        .outerjoin(CreditScore, CreditScore.application_id == CreditApplication.id)
        .order_by(CreditApplication.created_at.desc())
        .limit(limit)
    )

    if status:
        query = query.where(CreditApplication.status == status)

    result = await db.execute(query)
    rows = result.all()

    return [
        ApplicationSummary(
            application_id=str(app.id),
            applicant_name=user.full_name,
            applicant_email=user.email,
            age=app.age,
            income=app.income,
            loan_amount=app.loan_amount,
            status=app.status.value,
            credit_score=score.credit_score if score else None,
            is_approved=score.is_approved if score else None,
            created_at=app.created_at.strftime("%d %b %Y %H:%M") if app.created_at else "-",
        )
        for app, user, score in rows
    ]


@router.put("/applications/{application_id}")
async def update_application_status(
    application_id: str,
    body: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_loan_officer),
):
    """
    Update status aplikasi secara manual oleh loan officer.
    Misalnya override keputusan AI, atau tandai sebagai 'review'.
    """
    result = await db.execute(
        select(CreditApplication).where(CreditApplication.id == application_id)
    )
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Aplikasi tidak ditemukan")

    try:
        app.status = ApplicationStatus(body.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Status tidak valid: {body.status}")

    if body.rejection_reason:
        app.rejection_reason = body.rejection_reason

    await db.flush()
    return {"message": "Status berhasil diupdate", "status": body.status}