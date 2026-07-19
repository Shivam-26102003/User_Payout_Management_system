from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.user import UserResponse
from app.api.deps import get_db, get_current_user, require_admin
from app.repositories.user import UserRepository

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def read_user_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Returns details of the authenticated user."""
    return current_user

@router.get("", response_model=List[UserResponse])
async def read_users(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> List[User]:
    """Admin only: Lists all active users."""
    repo = UserRepository(db)
    return await repo.get_all(offset=offset, limit=limit)
