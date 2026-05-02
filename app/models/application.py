from sqlalchemy import Column, String, Float, Integer, DateTime, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum


class ApplicationStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    approved = "approved"
    rejected = "rejected"
    review = "review"


class CreditApplication(Base):
    __tablename__ = "credit_applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    applicant_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # ─── Data Pemohon ─────────────────────────────────────────
    age = Column(Integer, nullable=False)
    income = Column(Float, nullable=False)                 # pendapatan bulanan (Rp)
    loan_amount = Column(Float, nullable=False)            # jumlah pinjaman (Rp)
    loan_tenure_months = Column(Integer, nullable=False)   # tenor (bulan)
    employment_type = Column(String, nullable=False)       # pegawai_tetap / wiraswasta / freelance
    existing_debt = Column(Float, default=0.0)             # hutang existing (Rp)
    credit_history_score = Column(Integer, nullable=False) # 300-850
    num_dependents = Column(Integer, default=0)

    # ─── Status & Hasil ───────────────────────────────────────
    status = Column(SAEnum(ApplicationStatus), default=ApplicationStatus.pending)
    rejection_reason = Column(Text, nullable=True)

    # ─── Timestamps ───────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ─── Relationships ────────────────────────────────────────
    applicant = relationship("User", foreign_keys=[applicant_id])
    score = relationship("CreditScore", back_populates="application", uselist=False)

    def __repr__(self):
        return f"<CreditApplication {self.id} [{self.status}]>"