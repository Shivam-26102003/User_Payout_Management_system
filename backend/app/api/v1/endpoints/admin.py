from typing import List, Any
import uuid
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.reconciliation import BulkReconciliationRequest, ReconciliationJobResponse, SingleReconciliationRequest
from app.api.deps import get_db, require_admin
from app.services.reconciliation_service import ReconciliationService
from app.repositories.audit import AuditRepository
from app.repositories.reconciliation import ReconciliationRepository
from app.domain.value_objects.money import Money

router = APIRouter()

@router.post("/reconcile", response_model=ReconciliationJobResponse)
async def reconcile_sales(
    payload: BulkReconciliationRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> ReconciliationJobResponse:
    """Admin only: Bulk reconciles (approves/rejects) pending sales."""
    requests = [
        {"sale_id": item.sale_id, "action": item.action} for item in payload.sales
    ]
    
    job = await ReconciliationService.reconcile_sales(db, admin_user.id, requests)
    
    return ReconciliationJobResponse(
        job_id=job.id,
        status=job.status,
        reconciled_sales_count=len(payload.sales),
        error_details=job.error_details
    )

@router.get("/reconciliation-jobs")
async def list_reconciliation_jobs(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> List[Any]:
    """Admin only: Lists reconciliation tracker rows."""
    repo = ReconciliationRepository(db)
    jobs = await repo.get_all(offset=offset, limit=limit)
    return [
        {
            "id": str(j.id),
            "admin_id": str(j.admin_id),
            "status": j.status,
            "error_details": j.error_details,
            "created_at": j.created_at.isoformat()
        } for j in jobs
    ]

@router.get("/audit-logs")
async def get_audit_logs(
    action: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> dict:
    """Admin only: Fetches all activity audit logs for systemic review."""
    repo = AuditRepository(db)
    logs = await repo.list_audit_logs(action=action, offset=offset, limit=limit)
    total = await repo.get_total_audit_count(action=action)
    
    return {
        "logs": [
            {
                "id": str(l.id),
                "user_id": str(l.user_id) if l.user_id else None,
                "action": l.action,
                "target_table": l.target_table,
                "target_id": str(l.target_id) if l.target_id else None,
                "changes": l.changes,
                "ip_address": l.ip_address,
                "created_at": l.created_at.isoformat()
            } for l in logs
        ],
        "total": total
    }

@router.get("/affiliates")
async def list_affiliates(
    search: str | None = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> List[Any]:
    """Admin only: Lists all affiliate users with their current financial overview, pagination, search, and sorting."""
    from decimal import Decimal
    from app.models.balance import Balance
    from app.models.sale import Sale
    from app.domain.enums import UserRole, SaleStatus, AdvanceStatus
    from sqlalchemy import func, or_

    # Query all users with role USER
    query = select(User).where(User.role == UserRole.USER)
    if search:
        query = query.where(
            or_(
                User.name.icontains(search),
                User.email.icontains(search)
            )
        )
    users_res = await db.execute(query)
    users = users_res.scalars().all()

    results = []
    for u in users:
        # Get withdrawable balance
        bal_query = select(Balance).where(Balance.user_id == u.id)
        bal_res = await db.execute(bal_query)
        balance_obj = bal_res.scalars().first()
        withdrawable = balance_obj.withdrawable_balance if balance_obj else Decimal("0.0000")

        # Sum pending earnings
        pending_query = select(func.sum(Sale.earnings)).where(
            Sale.user_id == u.id,
            Sale.status == SaleStatus.PENDING,
            Sale.deleted_at.is_(None)
        )
        p_res = await db.execute(pending_query)
        pending_earnings = p_res.scalar() or Decimal("0.0000")

        # Sum advance paid
        advance_paid_query = select(func.sum(Sale.earnings * Decimal("0.10"))).where(
            Sale.user_id == u.id,
            Sale.status == SaleStatus.PENDING,
            Sale.advance_status == AdvanceStatus.PAID,
            Sale.deleted_at.is_(None)
        )
        adv_res = await db.execute(advance_paid_query)
        advance_paid = adv_res.scalar() or Decimal("0.0000")

        results.append({
            "id": str(u.id),
            "name": u.name,
            "email": u.email,
            "withdrawable_balance": float(withdrawable),
            "pending_earnings": float(pending_earnings),
            "advance_paid": float(advance_paid),
            "status": u.status.value
        })

    # Perform in-memory sorting
    reverse = sort_order.lower() == "desc"
    if sort_by in ["withdrawable_balance", "pending_earnings", "advance_paid"]:
        results.sort(key=lambda x: x[sort_by], reverse=reverse)
    else:
        results.sort(key=lambda x: str(x.get(sort_by, "")).lower(), reverse=reverse)

    return results

@router.get("/affiliates/{id}")
async def get_affiliate_details(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> Any:
    """Admin only: Fetches granular financial overview details for a single affiliate."""
    from decimal import Decimal
    from app.models.balance import Balance
    from app.models.sale import Sale
    from app.domain.enums import UserRole, SaleStatus, AdvanceStatus
    from sqlalchemy import func

    result = await db.execute(select(User).where(User.id == id, User.role == UserRole.USER))
    u = result.scalars().first()
    if not u:
        raise HTTPException(status_code=404, detail="Affiliate user not found")

    # Get withdrawable balance
    bal_query = select(Balance).where(Balance.user_id == u.id)
    bal_res = await db.execute(bal_query)
    balance_obj = bal_res.scalars().first()
    withdrawable = balance_obj.withdrawable_balance if balance_obj else Decimal("0.0000")

    # Sum pending earnings
    pending_query = select(func.sum(Sale.earnings)).where(
        Sale.user_id == u.id,
        Sale.status == SaleStatus.PENDING,
        Sale.deleted_at.is_(None)
    )
    p_res = await db.execute(pending_query)
    pending_earnings = p_res.scalar() or Decimal("0.0000")

    # Sum advance paid
    advance_paid_query = select(func.sum(Sale.earnings * Decimal("0.10"))).where(
        Sale.user_id == u.id,
        Sale.status == SaleStatus.PENDING,
        Sale.advance_status == AdvanceStatus.PAID,
        Sale.deleted_at.is_(None)
    )
    adv_res = await db.execute(advance_paid_query)
    advance_paid = adv_res.scalar() or Decimal("0.0000")

    return {
        "id": str(u.id),
        "name": u.name,
        "email": u.email,
        "withdrawable_balance": float(withdrawable),
        "pending_earnings": float(pending_earnings),
        "advance_paid": float(advance_paid),
        "status": u.status.value
    }

@router.get("/affiliates/{id}/ledger")
async def get_affiliate_ledger(
    id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> List[Any]:
    """Admin only: Lists ledger transactions scoped only to a single affiliate."""
    from app.repositories.ledger import LedgerRepository
    repo = LedgerRepository(db)
    return await repo.list_transactions(user_id=id, offset=offset, limit=limit)

@router.get("/affiliates/{id}/sales")
async def get_affiliate_sales(
    id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> List[Any]:
    """Admin only: Lists sales logs scoped only to a single affiliate."""
    from app.repositories.sale import SaleRepository
    from app.repositories.brand import BrandRepository
    from app.schemas.sale import SaleResponse
    sale_repo = SaleRepository(db)
    brand_repo = BrandRepository(db)
    sales = await sale_repo.list_sales(user_id=id, offset=offset, limit=limit)
    
    response_sales = []
    for s in sales:
        brand = await brand_repo.get_by_id(s.brand_id)
        brand_name = brand.name if brand else "unknown"
        response_sales.append(
            SaleResponse(
                id=s.id,
                user_id=s.user_id,
                brand_name=brand_name,
                external_id=s.external_id,
                amount=s.amount,
                earnings=s.earnings,
                status=s.status,
                advance_status=s.advance_status,
                reconciled_at=s.reconciled_at,
                created_at=s.created_at
            )
        )
    return response_sales

@router.get("/affiliates/{id}/withdrawals")
async def get_affiliate_withdrawals(
    id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> List[Any]:
    """Admin only: Lists withdrawal history scoped only to a single affiliate."""
    from app.repositories.withdrawal import WithdrawalRepository
    repo = WithdrawalRepository(db)
    return await repo.list_withdrawals(user_id=id, offset=offset, limit=limit)

@router.get("/withdrawals")
async def list_all_withdrawals(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> List[Any]:
    """Admin only: Lists all withdrawal requests across the system."""
    from app.repositories.withdrawal import WithdrawalRepository
    repo = WithdrawalRepository(db)
    return await repo.list_withdrawals(user_id=None, offset=offset, limit=limit)

@router.post("/reconcile/{sale_id}", response_model=ReconciliationJobResponse)
async def reconcile_single_sale(
    sale_id: uuid.UUID,
    payload: SingleReconciliationRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> ReconciliationJobResponse:
    """Admin only: Reconciles a single sale (Approve/Reject)."""
    requests = [
        {"sale_id": sale_id, "action": payload.action}
    ]
    job = await ReconciliationService.reconcile_sales(db, admin_user.id, requests)
    return ReconciliationJobResponse(
        job_id=job.id,
        status=job.status,
        reconciled_sales_count=1,
        error_details=job.error_details
    )

@router.post("/auto-approve/run")
async def trigger_auto_approval_job(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> dict:
    """Admin only: Manually trigger the daily auto-approval job to settle sales older than 7 days."""
    results = await ReconciliationService.run_auto_approval_job(db)
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    return {
        "message": "Auto approval job completed",
        "processed_count": len(results),
        "success_count": success_count,
        "details": results
    }
