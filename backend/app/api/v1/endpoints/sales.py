from decimal import Decimal
import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.sale import Sale
from app.models.brand import Brand
from app.schemas.sale import SaleCreate, SaleResponse
from app.api.deps import get_db, get_current_user, require_admin
from app.repositories.sale import SaleRepository
from app.repositories.brand import BrandRepository
from app.domain.enums import UserRole, SaleStatus, AdvanceStatus

router = APIRouter()

@router.post("", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
async def create_sale(
    payload: SaleCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> SaleResponse:
    """Admin only: Ingests an affiliate sale and calculates 10% earnings commission."""
    brand_repo = BrandRepository(db)
    brand = await brand_repo.get_by_name(payload.brand_name)
    if not brand:
        brand = Brand(name=payload.brand_name)
        await brand_repo.create(brand)
        await db.flush()

    sale_repo = SaleRepository(db)
    
    # Earning/commission is 10% of the sales recorded
    earnings_val = payload.amount * Decimal("0.10")
    
    sale = Sale(
        user_id=payload.user_id,
        brand_id=brand.id,
        external_id=payload.external_id,
        amount=payload.amount,
        earnings=earnings_val,
        status=SaleStatus.PENDING,
        advance_status=AdvanceStatus.PENDING
    )
    
    try:
        await sale_repo.create(sale)
        await db.flush()
        
        # Immediately credit 10% advance payout to the affiliate's ledger
        from app.services.advance_payout_service import AdvancePayoutService
        await AdvancePayoutService.process_sale_advance(db, sale)
        
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to ingest sale: {str(e)}"
        )
        
    return SaleResponse(
        id=sale.id,
        user_id=sale.user_id,
        brand_name=brand.name,
        external_id=sale.external_id,
        amount=sale.amount,
        earnings=sale.earnings,
        status=sale.status,
        advance_status=sale.advance_status,
        reconciled_at=sale.reconciled_at,
        created_at=sale.created_at
    )

@router.get("", response_model=List[SaleResponse])
async def read_sales(
    status: SaleStatus | None = None,
    user_id: uuid.UUID | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[SaleResponse]:
    """Lists sales. Standard users are restricted to viewing only their own sales."""
    sale_repo = SaleRepository(db)
    brand_repo = BrandRepository(db)

    # Restrict non-admins to their own user_id
    effective_user_id = user_id
    if current_user.role != UserRole.ADMIN:
        effective_user_id = current_user.id

    sales = await sale_repo.list_sales(
        user_id=effective_user_id,
        status=status,
        offset=offset,
        limit=limit
    )

    # Convert to response containing brand name
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
