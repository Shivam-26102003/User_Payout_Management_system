from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Index, JSON
from app.core.database import Base

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key = Column(String(255), primary_key=True)
    response_status = Column(Integer, nullable=False)
    response_body = Column(JSON, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<IdempotencyKey key={self.key} expires={self.expires_at}>"
