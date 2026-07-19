from typing import List
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sale import Sale
from app.domain.enums import SaleStatus, AdvanceStatus
from app.repositories.base import BaseRepository

class SaleRepository(BaseRepository[Sale]):
    def __init__(self, session: AsyncSession):
        super().__init__(Sale, session)

    async def get_sales_for_advance_payout(self) -> List[Sale]:
        """Find pending sales that have not received an advance payout yet."""
        result = await self.session.execute(
            select(Sale).where(
                and_(
                    Sale.status == SaleStatus.PENDING,
                    Sale.advance_status == AdvanceStatus.PENDING,
                    Sale.deleted_at.is_(None)
                )
            )
        )
        return list(result.scalars().all())

    async def list_sales(
        self,
        user_id: UUID | None = None,
        status: SaleStatus | None = None,
        offset: int = 0,
        limit: int = 100
    ) -> List[Sale]:
        """List sales with dynamic filters for dashboard use."""
        query = select(Sale).where(Sale.deleted_at.is_(None))
        if user_id:
            query = query.where(Sale.user_id == user_id)
        if status:
            query = query.where(Sale.status == status)
        
        query = query.order_by(Sale.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
        
    async def get_total_sales_count(
        self,
        user_id: UUID | None = None,
        status: SaleStatus | None = None
    ) -> int:
        from sqlalchemy import func
        query = select(func.count(Sale.id)).where(Sale.deleted_at.is_(None))
        if user_id:
            query = query.where(Sale.user_id == user_id)
        if status:
            query = query.where(Sale.status == status)
        result = await self.session.execute(query)
        return result.scalar() or 0
