import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_group_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True) # None for system account
    debit = Column(Numeric(18, 4), nullable=False, default=0.0)
    credit = Column(Numeric(18, 4), nullable=False, default=0.0)
    balance_type = Column(String(50), nullable=False)  # WITHDRAWABLE, RESERVE_ADVANCE, RESERVE_SYSTEM
    transaction_type = Column(String(50), nullable=False) # SALE_APPROVED, SALE_REJECTED, etc.
    reference_type = Column(String(50), nullable=False) # SALE, ADVANCE_PAYOUT, WITHDRAWAL
    reference_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_ledger_user_created", "user_id", "created_at"),
        Index("idx_ledger_group_id", "transaction_group_id"),
        Index("idx_ledger_ref_id", "reference_id"),
    )

    def __repr__(self) -> str:
        return f"<LedgerTransaction id={self.id} type={self.transaction_type} debit={self.debit} credit={self.credit}>"
