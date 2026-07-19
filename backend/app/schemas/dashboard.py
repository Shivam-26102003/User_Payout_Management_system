from decimal import Decimal
from typing import List
from pydantic import BaseModel

class ChartPoint(BaseModel):
    label: str
    value: Decimal

class DashboardStats(BaseModel):
    total_earnings: Decimal
    withdrawable_balance: Decimal
    pending_advance: Decimal
    total_withdrawn: Decimal
    sales_approved_count: int
    sales_pending_count: int
    sales_rejected_count: int
    earnings_chart: List[ChartPoint]
    withdrawals_chart: List[ChartPoint]
