from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.balance import Balance
from app.repositories.base import BaseRepository

class BalanceRepository(BaseRepository[Balance]):
    def __init__(self, session: AsyncSession):
        super().__init__(Balance, session)

    async def get_by_user_id(self, user_id: UUID) -> Balance | None:
        result = await self.session.execute(
            select(Balance).where(Balance.user_id == user_id)
        )
        return result.scalars().first()

    async def get_by_user_id_for_update(self, user_id: UUID) -> Balance | None:
        """Pessimistic lock on the balance row to serialize wallet actions."""
        query = select(Balance).where(Balance.user_id == user_id).with_for_update()
        result = await self.session.execute(query)
        return result.scalars().first()
