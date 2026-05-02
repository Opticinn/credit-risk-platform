from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base
import uuid


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    action = Column(String, nullable=False)        # LOGIN, SUBMIT_APPLICATION, VIEW_SCORE, dll
    resource = Column(String, nullable=True)       # application, score, user
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    detail = Column(JSONB, nullable=True)          # info tambahan
    ip_address = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AuditLog {self.action} by user={self.user_id}>"