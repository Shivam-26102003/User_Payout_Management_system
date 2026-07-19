import uuid
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.balance import BalanceResponse
from app.api.deps import get_db, get_current_user
from app.services.balance_service import BalanceService
from app.domain.enums import UserRole

router = APIRouter()

@router.get("", response_model=BalanceResponse)
async def read_balance(
    user_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> BalanceResponse:
    """Returns the withdrawable balance cache. Non-admins can only read their own balance."""
    target_user_id = current_user.id
    
    if user_id:
        if current_user.role != UserRole.ADMIN and user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. Cannot fetch other user's balance."
            )
        target_user_id = user_id
        
    balance = await BalanceService.get_or_create_balance(db, target_user_id)
    
    return BalanceResponse(
        user_id=target_user_id,
        withdrawable_balance=balance.withdrawable_balance,
        currency="INR"
    )
