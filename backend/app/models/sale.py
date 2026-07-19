import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from app.domain.enums import SaleStatus, AdvanceStatus

class Sale(Base):
    __tablename__ = "sales"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)
    external_id = Column(String(255), unique=True, index=True, nullable=False)
    amount = Column(Numeric(18, 4), nullable=False)
    earnings = Column(Numeric(18, 4), nullable=False)
    status = Column(String(50), nullable=False, default=SaleStatus.PENDING)
    advance_status = Column(String(50), nullable=False, default=AdvanceStatus.PENDING)
    reconciliation_job_id = Column(UUID(as_uuid=True), ForeignKey("reconciliation_jobs.id"), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    reconciled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_sales_status", "status"),
        Index("idx_sales_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Sale id={self.id} status={self.status} external_id={self.external_id}>"
