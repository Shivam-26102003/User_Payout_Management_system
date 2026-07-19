import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class SystemJob(Base):
    __tablename__ = "system_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_name = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(String(50), nullable=False)  # IDLE, RUNNING, FAILED
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    error_log = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<SystemJob job_name={self.job_name} status={self.status}>"
