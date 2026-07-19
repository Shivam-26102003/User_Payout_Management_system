import uuid
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.ledger import LedgerResponse
from app.api.deps import get_db, get_current_user
from app.repositories.ledger import LedgerRepository
from app.domain.enums import UserRole

router = APIRouter()

@router.get("", response_model=List[LedgerResponse])
async def read_ledger_transactions(
    user_id: uuid.UUID | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[LedgerResponse]:
    """Retrieves ledger transaction history. Standard users are restricted to their own entries."""
    repo = LedgerRepository(db)
    
    effective_user_id = user_id
    if current_user.role != UserRole.ADMIN:
        effective_user_id = current_user.id
        
    return await repo.list_transactions(
        user_id=effective_user_id,
        offset=offset,
        limit=limit
    )

