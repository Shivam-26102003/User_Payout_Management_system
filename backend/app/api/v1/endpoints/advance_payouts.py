from typing import List, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.advance_payout import AdvancePayout
from app.api.deps import get_db, require_admin, get_current_user
from app.services.advance_payout_service import AdvancePayoutService

router = APIRouter()

@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
async def trigger_advance_payout(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> dict:
    """Admin only: Triggers the background job to distribute 10% advances on pending sales."""
    # Run inline synchronously for simplicity and testing immediacy in local docker runs
    results = await AdvancePayoutService.process_eligible_advance_payouts(db)
    processed_count = sum(1 for r in results if r["status"] == "SUCCESS")
    return {
        "message": "Advance payout job completed",
        "processed_count": processed_count,
        "details": results
    }

@router.get("/history")
async def get_advance_payout_history(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Any]:
    """Retrieves list of advance payouts. Standard users are restricted to their own entries."""
    from app.domain.enums import UserRole
    
    query = select(AdvancePayout)
    if current_user.role != UserRole.ADMIN:
        query = query.where(AdvancePayout.user_id == current_user.id)
        
    query = query.order_by(AdvancePayout.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    payouts = result.scalars().all()
    
    return [
        {
            "id": str(p.id),
            "sale_id": str(p.sale_id),
            "user_id": str(p.user_id),
            "amount": float(p.amount),
            "status": p.status,
            "created_at": p.created_at.isoformat()
        } for p in payouts
    ]
