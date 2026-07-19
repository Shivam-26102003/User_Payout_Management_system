import uuid
from typing import List
from pydantic import BaseModel
from app.domain.enums import SaleStatus

class ReconcileSaleItem(BaseModel):
    sale_id: uuid.UUID
    action: SaleStatus  # APPROVED or REJECTED

class BulkReconciliationRequest(BaseModel):
    sales: List[ReconcileSaleItem]

class ReconciliationJobResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    reconciled_sales_count: int
    error_details: str | None = None

class SingleReconciliationRequest(BaseModel):
    action: SaleStatus  # APPROVED or REJECTED
