import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from app.domain.enums import LedgerTransactionType, LedgerBalanceType

class LedgerResponse(BaseModel):
    id: uuid.UUID
    transaction_group_id: uuid.UUID
    user_id: uuid.UUID | None
    debit: Decimal
    credit: Decimal
    balance_type: LedgerBalanceType
    transaction_type: LedgerTransactionType
    reference_type: str
    reference_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
