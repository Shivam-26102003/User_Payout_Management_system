import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ledger import LedgerTransaction
from app.domain.enums import LedgerTransactionType, LedgerBalanceType
from app.domain.value_objects.money import Money

class LedgerService:
    @staticmethod
    async def record_transaction(
        session: AsyncSession,
        user_id: uuid.UUID | None,
        amount: Money,
        transaction_type: LedgerTransactionType,
        reference_type: str,
        reference_id: uuid.UUID
    ) -> uuid.UUID:
        """
        Creates exactly two ledger entries (Debit and Credit) to ensure balanced double-entry accounting.
        Returns the transaction_group_id.
        """
        transaction_group_id = uuid.uuid4()
        abs_amount = abs(amount.amount)

        # Decide which system reserve account to hit
        if transaction_type == LedgerTransactionType.ADVANCE_PAYOUT:
            reserve_type = LedgerBalanceType.RESERVE_ADVANCE
        else:
            reserve_type = LedgerBalanceType.RESERVE_SYSTEM

        # User Entry & Reserve Entry
        if amount.amount >= 0:
            # User gets credited, System gets debited
            user_entry = LedgerTransaction(
                transaction_group_id=transaction_group_id,
                user_id=user_id,
                debit=Decimal("0.0000"),
                credit=abs_amount,
                balance_type=LedgerBalanceType.WITHDRAWABLE,
                transaction_type=transaction_type,
                reference_type=reference_type,
                reference_id=reference_id
            )
            reserve_entry = LedgerTransaction(
                transaction_group_id=transaction_group_id,
                user_id=None,  # Corporate system reserve
                debit=abs_amount,
                credit=Decimal("0.0000"),
                balance_type=reserve_type,
                transaction_type=transaction_type,
                reference_type=reference_type,
                reference_id=reference_id
            )
        else:
            # User gets debited, System gets credited
            user_entry = LedgerTransaction(
                transaction_group_id=transaction_group_id,
                user_id=user_id,
                debit=abs_amount,
                credit=Decimal("0.0000"),
                balance_type=LedgerBalanceType.WITHDRAWABLE,
                transaction_type=transaction_type,
                reference_type=reference_type,
                reference_id=reference_id
            )
            reserve_entry = LedgerTransaction(
                transaction_group_id=transaction_group_id,
                user_id=None,
                debit=Decimal("0.0000"),
                credit=abs_amount,
                balance_type=reserve_type,
                transaction_type=transaction_type,
                reference_type=reference_type,
                reference_id=reference_id
            )

        session.add(user_entry)
        session.add(reserve_entry)
        await session.flush()
        
        return transaction_group_id
