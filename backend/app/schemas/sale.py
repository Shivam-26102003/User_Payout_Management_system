import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from app.domain.enums import SaleStatus, AdvanceStatus

class SaleCreate(BaseModel):
    user_id: uuid.UUID
    brand_name: str
    external_id: str
    amount: Decimal = Field(gt=0, decimal_places=4)

class SaleResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    brand_name: str
    external_id: str
    amount: Decimal
    earnings: Decimal
    status: SaleStatus
    advance_status: AdvanceStatus
    reconciled_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True
