import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True) # System actions might not have user
    action = Column(String(255), nullable=False)
    target_table = Column(String(100), nullable=True)
    target_id = Column(UUID(as_uuid=True), nullable=True)
    changes = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_audit_logs_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog action={self.action} user_id={self.user_id}>"
