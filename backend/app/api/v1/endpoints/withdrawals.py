import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.withdrawal import WithdrawalRequest
from app.schemas.withdrawal import WithdrawalCreate, WithdrawalResponse, WithdrawalStatusUpdate
from app.api.deps import get_db, get_current_user, require_admin
from app.repositories.withdrawal import WithdrawalRepository
from app.services.withdrawal_service import WithdrawalService
from app.domain.enums import UserRole, WithdrawalStatus
from app.domain.value_objects.money import Money
from app.domain.exceptions import DomainException

router = APIRouter()

@router.post("", response_model=WithdrawalResponse, status_code=status.HTTP_201_CREATED)
async def request_withdrawal(
    payload: WithdrawalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> WithdrawalRequest:
    """Enqueues a payout withdrawal request, locking funds and verifying the 24-hour rule."""
    amount_money = Money(payload.amount, payload.currency)
    
    try:
        withdrawal = await WithdrawalService.request_withdrawal(
            session=db,
            user_id=current_user.id,
            amount=amount_money
        )
        await db.commit()
        return withdrawal
    except DomainException as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/me", response_model=List[WithdrawalResponse])
async def list_my_withdrawals(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[WithdrawalRequest]:
    """Lists only the currently authenticated user's withdrawal requests."""
    repo = WithdrawalRepository(db)
    return await repo.list_withdrawals(
        user_id=current_user.id,
        offset=offset,
        limit=limit
    )

@router.get("", response_model=List[WithdrawalResponse])
async def list_withdrawals(
    user_id: uuid.UUID | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[WithdrawalRequest]:
    """Lists withdrawal requests. Standard users see only their own requests."""
    repo = WithdrawalRepository(db)
    
    effective_user_id = user_id
    if current_user.role != UserRole.ADMIN:
        effective_user_id = current_user.id
        
    return await repo.list_withdrawals(
        user_id=effective_user_id,
        offset=offset,
        limit=limit
    )

@router.get("/{id}", response_model=WithdrawalResponse)
async def get_withdrawal(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> WithdrawalRequest:
    """Gets details of a specific withdrawal."""
    repo = WithdrawalRepository(db)
    withdrawal = await repo.get_by_id(id)
    if not withdrawal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Withdrawal not found"
        )
        
    if current_user.role != UserRole.ADMIN and withdrawal.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
        
    return withdrawal

@router.patch("/{id}", response_model=WithdrawalResponse)
async def update_withdrawal_status(
    id: uuid.UUID,
    payload: WithdrawalStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> WithdrawalRequest:
    """
    Admin/System webhook simulation: Updates payout status.
    Transitioning to FAILED/CANCELLED triggers a refund of funds back to the user's balance.
    """
    try:
        if payload.status in [WithdrawalStatus.FAILED, WithdrawalStatus.CANCELLED]:
            withdrawal = await WithdrawalService.process_withdrawal_recovery(
                session=db,
                withdrawal_id=id,
                target_status=payload.status,
                failure_reason=payload.failure_reason
            )
        elif payload.status == WithdrawalStatus.COMPLETED:
            withdrawal = await WithdrawalService.complete_withdrawal(
                session=db,
                withdrawal_id=id
            )
        else:
            # Shift to standard processing status
            repo = WithdrawalRepository(db)
            withdrawal = await repo.get_by_id(id)
            if not withdrawal:
                raise HTTPException(status_code=404, detail="Withdrawal not found")
            withdrawal.status = payload.status
            await db.flush()
            
        await db.commit()
        return withdrawal
        
    except DomainException as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
