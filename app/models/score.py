from sqlalchemy import Column, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


class CreditScore(Base):
    __tablename__ = "credit_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("credit_applications.id"), nullable=False, unique=True)

    # ─── Hasil ML ─────────────────────────────────────────────
    probability_default = Column(Float, nullable=False)  # 0.0 - 1.0
    credit_score = Column(Float, nullable=False)         # 0 - 100
    is_approved = Column(Boolean, nullable=False)

    # ─── SHAP Explainability ──────────────────────────────────
    shap_values = Column(JSONB, nullable=True)           # {feature: shap_value}
    top_factors = Column(JSONB, nullable=True)           # [{"factor": "...", "impact": "positive/negative"}]

    # ─── AI Explanation (Gemini) ──────────────────────────────
    ai_explanation = Column(Text, nullable=True)         # Penjelasan natural language dari Gemini

    # ─── Model Info ───────────────────────────────────────────
    model_version = Column(Text, default="v1.0")
    scored_at = Column(DateTime(timezone=True), server_default=func.now())

    # ─── Relationships ────────────────────────────────────────
    application = relationship("CreditApplication", back_populates="score")

    def __repr__(self):
        return f"<CreditScore app={self.application_id} score={self.credit_score:.1f}>"