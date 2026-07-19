import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from app.domain.enums import WithdrawalStatus

class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(18, 4), nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    status = Column(String(50), nullable=False, default=WithdrawalStatus.PENDING)
    idempotency_key = Column(String(255), unique=True, nullable=True)
    failure_reason = Column(String(500), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_withdrawals_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<WithdrawalRequest id={self.id} user_id={self.user_id} status={self.status} amount={self.amount}>"
