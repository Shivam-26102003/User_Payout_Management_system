from datetime import datetime, timedelta
from typing import List
from uuid import UUID
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.withdrawal import WithdrawalRequest
from app.domain.enums import WithdrawalStatus
from app.repositories.base import BaseRepository

class WithdrawalRepository(BaseRepository[WithdrawalRequest]):
    def __init__(self, session: AsyncSession):
        super().__init__(WithdrawalRequest, session)

    async def get_last_withdrawal_within_24h(self, user_id: UUID) -> WithdrawalRequest | None:
        """Finds any non-failed, non-cancelled withdrawal initiated by the user in the last 24 hours."""
        time_limit = datetime.utcnow() - timedelta(hours=24)
        query = select(WithdrawalRequest).where(
            and_(
                WithdrawalRequest.user_id == user_id,
                WithdrawalRequest.created_at >= time_limit,
                WithdrawalRequest.status.in_([
                    WithdrawalStatus.PENDING,
                    WithdrawalStatus.PROCESSING,
                    WithdrawalStatus.COMPLETED
                ])
            )
        ).order_by(WithdrawalRequest.created_at.desc()).limit(1)
        
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_withdrawals(
        self,
        user_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100
    ) -> List[WithdrawalRequest]:
        query = select(WithdrawalRequest)
        if user_id:
            query = query.where(WithdrawalRequest.user_id == user_id)
        query = query.order_by(WithdrawalRequest.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_total_withdrawals_count(self, user_id: UUID | None = None) -> int:
        query = select(func.count(WithdrawalRequest.id))
        if user_id:
            query = query.where(WithdrawalRequest.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar() or 0
