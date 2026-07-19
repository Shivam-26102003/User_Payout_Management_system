from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.security import verify_password, create_access_token, get_password_hash
from app.models.user import User
from app.models.balance import Balance
from app.schemas.auth import Token, LoginRequest
from app.schemas.user import UserCreate, UserResponse
from app.api.deps import get_db

router = APIRouter()

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Public registration: Creates a new user and provisions their balance tracker."""
    # Check if email is already taken
    result = await db.execute(select(User).where(User.email == payload.email, User.deleted_at.is_(None)))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered."
        )

    # Hash the password and save
    hashed = get_password_hash(payload.password)
    user = User(
        email=payload.email,
        password_hash=hashed,
        name=payload.name,
        role=payload.role,
        status=payload.status
    )
    db.add(user)
    await db.flush()

    # Provision zero balance cache
    balance = Balance(
        user_id=user.id,
        withdrawable_balance=0.0
    )
    db.add(balance)
    
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Signup failed: {str(e)}"
        )

    return user

@router.post("/token", response_model=Token)
async def login_for_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Token:
    """Authenticates credentials and returns a JWT access token."""
    result = await db.execute(select(User).where(User.email == form_data.username, User.deleted_at.is_(None)))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role
    )
