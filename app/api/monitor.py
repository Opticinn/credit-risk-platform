"""
Monitor Router — Endpoint untuk monitoring platform

Endpoint:
- GET  /monitor/health          → cek kesehatan semua komponen
- GET  /monitor/drift           → jalankan drift detection
- POST /monitor/alert/test      → test kirim alert Telegram
- GET  /monitor/stats/daily     → statistik harian + kirim ke Telegram
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from datetime import datetime, date
import pandas as pd

from app.database import get_db
from app.models.user import User
from app.models.application import CreditApplication, ApplicationStatus
from app.models.score import CreditScore
from app.services.auth import get_current_loan_officer
from app.services.monitoring.alerting import alerting_service
from app.services.monitoring.drift_detector import drift_detector

router = APIRouter()


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_loan_officer),
):
    """
    Cek kesehatan semua komponen platform.
    
    Seperti medical check-up — cek satu per satu apakah
    semua organ (komponen) berfungsi normal.
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }

    # Cek Database
    try:
        await db.execute(select(func.count(User.id)))
        health["components"]["database"] = "✅ OK"
    except Exception as e:
        health["components"]["database"] = f"❌ Error: {str(e)}"
        health["status"] = "unhealthy"

    # Cek ML Model
    try:
        from app.services.ml.scoring import scoring_service
        if scoring_service._loaded:
            health["components"]["ml_model"] = "✅ OK"
        else:
            health["components"]["ml_model"] = "⚠️ Not loaded"
    except Exception as e:
        health["components"]["ml_model"] = f"❌ Error: {str(e)}"

    # Cek RAG Service
    try:
        from app.services.rag.rag_service import rag_service
        if rag_service._loaded:
            health["components"]["rag_service"] = f"✅ OK ({rag_service.collection.count()} chunks)"
        else:
            health["components"]["rag_service"] = "⚠️ Not loaded"
    except Exception as e:
        health["components"]["rag_service"] = f"❌ Error: {str(e)}"

    # Cek Telegram
    try:
        if alerting_service.token and alerting_service.chat_id:
            health["components"]["telegram"] = "✅ Configured"
        else:
            health["components"]["telegram"] = "⚠️ Not configured"
    except Exception as e:
        health["components"]["telegram"] = f"❌ Error: {str(e)}"

    return health


@router.get("/drift")
async def run_drift_detection(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_loan_officer),
):
    """
    Jalankan drift detection — bandingkan data terbaru dengan data training.
    
    Mengambil 100 aplikasi terbaru dari database,
    lalu dibandingkan distribusinya dengan data training.
    """
    # Ambil data terbaru dari database
    result = await db.execute(
        select(CreditApplication)
        .order_by(CreditApplication.created_at.desc())
        .limit(100)
    )
    applications = result.scalars().all()

    if len(applications) < 10:
        return {
            "drift_detected": False,
            "reason": f"Data terlalu sedikit ({len(applications)} aplikasi). Butuh minimal 10.",
            "tip": "Submit lebih banyak aplikasi kredit untuk analisis drift yang akurat."
        }

    # Konversi ke DataFrame dengan nama kolom yang sama dengan dataset training
    current_df = pd.DataFrame([{
        "person_age": app.age,
        "person_income": app.income,
        "loan_amnt": app.loan_amount,
        "loan_int_rate": 11.0,  # default
        "loan_percent_income": app.loan_amount / app.income if app.income > 0 else 0,
        "cb_person_cred_hist_length": 2,  # default
    } for app in applications])

    # Jalankan deteksi
    drift_detector.load_reference()
    report = drift_detector.detect(current_df)

    return report


@router.post("/alert/test")
async def test_alert(
    current_user: User = Depends(get_current_loan_officer),
):
    """Test kirim notifikasi ke Telegram."""
    success = alerting_service.send_startup_notice()
    return {
        "success": success,
        "message": "Alert terkirim!" if success else "Gagal kirim alert — cek konfigurasi Telegram"
    }


@router.get("/stats/daily")
async def daily_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_loan_officer),
):
    """
    Statistik harian dan kirim laporan ke Telegram.
    Endpoint ini bisa dipanggil otomatis setiap hari via scheduler.
    """
    today = date.today()

    # Hitung aplikasi hari ini
    result = await db.execute(
        select(func.count(CreditApplication.id))
        .where(cast(CreditApplication.created_at, Date) == today)
    )
    total_today = result.scalar() or 0

    # Hitung per status hari ini
    result = await db.execute(
        select(CreditApplication.status, func.count(CreditApplication.id))
        .where(cast(CreditApplication.created_at, Date) == today)
        .group_by(CreditApplication.status)
    )
    status_counts = dict(result.all())

    approved = status_counts.get(ApplicationStatus.approved, 0)
    rejected = status_counts.get(ApplicationStatus.rejected, 0)

    # Rata-rata credit score hari ini
    result = await db.execute(
        select(func.avg(CreditScore.credit_score))
        .join(CreditApplication, CreditApplication.id == CreditScore.application_id)
        .where(cast(CreditApplication.created_at, Date) == today)
    )
    avg_score = result.scalar() or 0.0

    stats = {
        "date": today.isoformat(),
        "total_today": total_today,
        "approved": approved,
        "rejected": rejected,
        "avg_score": float(avg_score),
        "approval_rate": (approved / total_today * 100) if total_today > 0 else 0.0,
    }

    # Kirim ke Telegram
    alerting_service.send_daily_report(stats)

    return stats