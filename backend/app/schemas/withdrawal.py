import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from app.domain.enums import WithdrawalStatus

class WithdrawalCreate(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=4)
    currency: str = "INR"

class WithdrawalResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    amount: Decimal
    currency: str
    status: WithdrawalStatus
    failure_reason: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True

class WithdrawalStatusUpdate(BaseModel):
    status: WithdrawalStatus
    failure_reason: str | None = None
