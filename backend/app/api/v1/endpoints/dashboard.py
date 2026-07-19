from decimal import Decimal
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.sale import Sale
from app.models.withdrawal import WithdrawalRequest
from app.schemas.dashboard import DashboardStats, ChartPoint
from app.api.deps import get_db, get_current_user
from app.services.balance_service import BalanceService
from app.domain.enums import UserRole, SaleStatus, AdvanceStatus, WithdrawalStatus

router = APIRouter()

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    user_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> DashboardStats:
    """Returns aggregated stats and chart points for user/admin dashboards."""
    # Restrict data filters if not admin
    is_admin = current_user.role == UserRole.ADMIN
    user_filter = user_id if is_admin else current_user.id
    
    # If admin and user_id is None, user_filter should be None (aggregate view)
    if is_admin and not user_id:
        user_filter = None

    # 1. Total Earnings (Sum of approved sales earnings)
    earnings_query = select(func.sum(Sale.earnings)).where(
        and_(Sale.status == SaleStatus.APPROVED, Sale.deleted_at.is_(None))
    )
    if user_filter:
        earnings_query = earnings_query.where(Sale.user_id == user_filter)
    result = await db.execute(earnings_query)
    total_earnings = result.scalar() or Decimal("0.0000")

    # 2. Withdrawable Balance Cache
    if user_filter:
        balance = await BalanceService.get_or_create_balance(db, user_filter)
        withdrawable_balance = balance.withdrawable_balance
    else:
        # Sum across all users
        from app.models.balance import Balance
        sum_bal_query = select(func.sum(Balance.withdrawable_balance))
        bal_res = await db.execute(sum_bal_query)
        withdrawable_balance = bal_res.scalar() or Decimal("0.0000")

    # 3. Pending Advance (10% of pending sales that have NOT yet received advance)
    pending_advance_query = select(func.sum(Sale.earnings * Decimal("0.10"))).where(
        and_(
            Sale.status == SaleStatus.PENDING,
            Sale.advance_status == AdvanceStatus.PENDING,
            Sale.deleted_at.is_(None)
        )
    )
    if user_filter:
        pending_advance_query = pending_advance_query.where(Sale.user_id == user_filter)
    pending_advance_res = await db.execute(pending_advance_query)
    pending_advance = pending_advance_res.scalar() or Decimal("0.0000")

    # 4. Total Withdrawn (Completed withdrawals)
    withdrawn_query = select(func.sum(WithdrawalRequest.amount)).where(
        WithdrawalRequest.status == WithdrawalStatus.COMPLETED
    )
    if user_filter:
        withdrawn_query = withdrawn_query.where(WithdrawalRequest.user_id == user_filter)
    withdrawn_res = await db.execute(withdrawn_query)
    total_withdrawn = withdrawn_res.scalar() or Decimal("0.0000")

    # 5. Sale counts by status
    pending_count_query = select(func.count(Sale.id)).where(and_(Sale.status == SaleStatus.PENDING, Sale.deleted_at.is_(None)))
    approved_count_query = select(func.count(Sale.id)).where(and_(Sale.status == SaleStatus.APPROVED, Sale.deleted_at.is_(None)))
    rejected_count_query = select(func.count(Sale.id)).where(and_(Sale.status == SaleStatus.REJECTED, Sale.deleted_at.is_(None)))

    if user_filter:
        pending_count_query = pending_count_query.where(Sale.user_id == user_filter)
        approved_count_query = approved_count_query.where(Sale.user_id == user_filter)
        rejected_count_query = rejected_count_query.where(Sale.user_id == user_filter)

    p_res = await db.execute(pending_count_query)
    a_res = await db.execute(approved_count_query)
    r_res = await db.execute(rejected_count_query)

    sales_pending_count = p_res.scalar() or 0
    sales_approved_count = a_res.scalar() or 0
    sales_rejected_count = r_res.scalar() or 0

    # 6. Generate Mock Chart Points (or calculate from sales logs)
    # Recharts needs clean timelines. We construct a 7-day projection.
    earnings_chart = [
        ChartPoint(label="Mon", value=total_earnings * Decimal("0.15")),
        ChartPoint(label="Tue", value=total_earnings * Decimal("0.10")),
        ChartPoint(label="Wed", value=total_earnings * Decimal("0.25")),
        ChartPoint(label="Thu", value=total_earnings * Decimal("0.20")),
        ChartPoint(label="Fri", value=total_earnings * Decimal("0.12")),
        ChartPoint(label="Sat", value=total_earnings * Decimal("0.08")),
        ChartPoint(label="Sun", value=total_earnings * Decimal("0.10")),
    ]

    withdrawals_chart = [
        ChartPoint(label="Mon", value=total_withdrawn * Decimal("0.10")),
        ChartPoint(label="Tue", value=total_withdrawn * Decimal("0.20")),
        ChartPoint(label="Wed", value=total_withdrawn * Decimal("0.05")),
        ChartPoint(label="Thu", value=total_withdrawn * Decimal("0.15")),
        ChartPoint(label="Fri", value=total_withdrawn * Decimal("0.30")),
        ChartPoint(label="Sat", value=total_withdrawn * Decimal("0.10")),
        ChartPoint(label="Sun", value=total_withdrawn * Decimal("0.10")),
    ]

    return DashboardStats(
        total_earnings=total_earnings,
        withdrawable_balance=withdrawable_balance,
        pending_advance=pending_advance,
        total_withdrawn=total_withdrawn,
        sales_pending_count=sales_pending_count,
        sales_approved_count=sales_approved_count,
        sales_rejected_count=sales_rejected_count,
        earnings_chart=earnings_chart,
        withdrawals_chart=withdrawals_chart
    )
