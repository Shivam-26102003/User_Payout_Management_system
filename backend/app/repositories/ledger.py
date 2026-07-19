from typing import List
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ledger import LedgerTransaction
from app.repositories.base import BaseRepository

class LedgerRepository(BaseRepository[LedgerTransaction]):
    def __init__(self, session: AsyncSession):
        super().__init__(LedgerTransaction, session)

    async def list_transactions(
        self,
        user_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100
    ) -> List[LedgerTransaction]:
        query = select(LedgerTransaction)
        if user_id:
            query = query.where(LedgerTransaction.user_id == user_id)
        
        query = query.order_by(LedgerTransaction.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_total_transactions_count(self, user_id: UUID | None = None) -> int:
        query = select(func.count(LedgerTransaction.id))
        if user_id:
            query = query.where(LedgerTransaction.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar() or 0
