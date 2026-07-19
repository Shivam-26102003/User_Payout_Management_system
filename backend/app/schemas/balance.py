import uuid
from decimal import Decimal
from pydantic import BaseModel

class BalanceResponse(BaseModel):
    user_id: uuid.UUID
    withdrawable_balance: Decimal
    currency: str
