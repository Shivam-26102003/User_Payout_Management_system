import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.balance import Balance
from app.repositories.balance import BalanceRepository
from app.domain.value_objects.money import Money
from app.domain.exceptions import EntityNotFoundException

class BalanceService:
    @staticmethod
    async def get_or_create_balance(session: AsyncSession, user_id: uuid.UUID) -> Balance:
        balance_repo = BalanceRepository(session)
        balance = await balance_repo.get_by_user_id(user_id)
        if not balance:
            balance = Balance(
                user_id=user_id,
                withdrawable_balance=Decimal("0.0000"),
                version=1
            )
            await balance_repo.create(balance)
        return balance

    @staticmethod
    async def get_or_create_balance_for_update(session: AsyncSession, user_id: uuid.UUID) -> Balance:
        """Pessimistic locked balance retrieval."""
        balance_repo = BalanceRepository(session)
        balance = await balance_repo.get_by_user_id_for_update(user_id)
        if not balance:
            balance = Balance(
                user_id=user_id,
                withdrawable_balance=Decimal("0.0000"),
                version=1
            )
            await balance_repo.create(balance)
            # Re-fetch with lock
            balance = await balance_repo.get_by_user_id_for_update(user_id)
            if not balance:
                raise EntityNotFoundException(f"Failed to lock user balance for user {user_id}")
        return balance

    @classmethod
    async def adjust_balance(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        amount: Money
    ) -> Balance:
        """Lock balance, apply adjustment, increment version."""
        balance = await self.get_or_create_balance_for_update(session, user_id)
        
        current_amount = Money(balance.withdrawable_balance, amount.currency)
        new_amount = current_amount + amount
        
        balance.withdrawable_balance = new_amount.amount
        balance.version += 1
        
        await session.flush()
        return balance
