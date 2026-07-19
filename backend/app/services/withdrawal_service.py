import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.withdrawal import WithdrawalRequest
from app.repositories.withdrawal import WithdrawalRepository
from app.repositories.balance import BalanceRepository
from app.services.ledger_service import LedgerService
from app.services.balance_service import BalanceService
from app.services.notification_service import NotificationService
from app.domain.enums import WithdrawalStatus, LedgerTransactionType
from app.domain.value_objects.money import Money
from app.domain.exceptions import (
    InsufficientFundsException,
    CooldownActiveException,
    EntityNotFoundException,
    InvalidWithdrawalStatusException
)

class WithdrawalService:
    @staticmethod
    async def request_withdrawal(
        session: AsyncSession,
        user_id: uuid.UUID,
        amount: Money,
        idempotency_key: str | None = None
    ) -> WithdrawalRequest:
        """
        Locks user balance, checks 24-hour cooldown, and records a pending withdrawal.
        Debits user balance and writes balanced double-entry rows.
        """
        withdrawal_repo = WithdrawalRepository(session)

        # 1. Enforce 24-Hour Cooldown constraint
        last_withdrawal = await withdrawal_repo.get_last_withdrawal_within_24h(user_id)
        if last_withdrawal:
            raise CooldownActiveException(
                f"Cooldown active. Last withdrawal was initiated at {last_withdrawal.created_at}"
            )

        # 2. Lock User Balance (Pessimistic Lock)
        balance_repo = BalanceRepository(session)
        balance = await balance_repo.get_by_user_id_for_update(user_id)
        if not balance:
            # Auto-create balance if somehow missing
            balance = await BalanceService.get_or_create_balance_for_update(session, user_id)

        # 3. Check sufficient funds
        user_balance = Money(balance.withdrawable_balance, amount.currency)
        if user_balance < amount:
            raise InsufficientFundsException(
                f"Insufficient funds. Balance is {user_balance}, requested {amount}"
            )

        # 4. Create Withdrawal Request
        withdrawal = WithdrawalRequest(
            user_id=user_id,
            amount=amount.amount,
            currency=amount.currency,
            status=WithdrawalStatus.PENDING,
            idempotency_key=idempotency_key
        )
        await withdrawal_repo.create(withdrawal)
        await session.flush()

        # 5. Record Double-Entry Transaction
        # Debit User withdrawable (-Amount), Credit System Payout Reserve (+Amount)
        debit_amount = Money(-amount.amount, amount.currency)
        await LedgerService.record_transaction(
            session=session,
            user_id=user_id,
            amount=debit_amount,
            transaction_type=LedgerTransactionType.WITHDRAWAL_INITIATED,
            reference_type="WITHDRAWAL",
            reference_id=withdrawal.id
        )

        # 6. Adjust Balance Cache
        await BalanceService.adjust_balance(
            session=session,
            user_id=user_id,
            amount=debit_amount
        )

        # 7. Notify User
        await NotificationService.send_notification(
            session=session,
            user_id=user_id,
            notification_type="WITHDRAWAL_INITIATED",
            message=f"Withdrawal request of {amount} is initiated and is pending processing."
        )

        return withdrawal

    @staticmethod
    async def process_withdrawal_recovery(
        session: AsyncSession,
        withdrawal_id: uuid.UUID,
        target_status: WithdrawalStatus,
        failure_reason: str | None = None
    ) -> WithdrawalRequest:
        """
        Failed Payout Recovery.
        If a payout fails, cancels, or gets rejected, refund the funds back to user's balance
        and mark withdrawal request status.
        """
        if target_status not in [WithdrawalStatus.FAILED, WithdrawalStatus.CANCELLED]:
            raise InvalidWithdrawalStatusException(
                f"Recovery service can only transition to FAILED or CANCELLED status"
            )

        withdrawal_repo = WithdrawalRepository(session)
        withdrawal = await withdrawal_repo.get_by_id(withdrawal_id)
        if not withdrawal:
            raise EntityNotFoundException(f"Withdrawal request {withdrawal_id} not found")

        # Only process pending/processing status for recovery
        if withdrawal.status in [WithdrawalStatus.COMPLETED, WithdrawalStatus.FAILED, WithdrawalStatus.CANCELLED]:
            return withdrawal  # Already finalized

        # Lock User Balance row (Pessimistic Lock)
        balance_repo = BalanceRepository(session)
        await balance_repo.get_by_user_id_for_update(withdrawal.user_id)

        # Calculate refund Money
        refund_amount = Money(withdrawal.amount, withdrawal.currency)

        # Record double-entry Ledger refund
        # Credit User withdrawable (+Amount), Debit System Payout Reserve (-Amount)
        tx_type = (
            LedgerTransactionType.WITHDRAWAL_FAILED 
            if target_status == WithdrawalStatus.FAILED 
            else LedgerTransactionType.WITHDRAWAL_INITIATED  # Re-credit using WITHDRAWAL_FAILED equivalent
        )
        
        await LedgerService.record_transaction(
            session=session,
            user_id=withdrawal.user_id,
            amount=refund_amount,
            transaction_type=LedgerTransactionType.WITHDRAWAL_FAILED,
            reference_type="WITHDRAWAL",
            reference_id=withdrawal.id
        )

        # Update user's balance cache (+Refund)
        await BalanceService.adjust_balance(
            session=session,
            user_id=withdrawal.user_id,
            amount=refund_amount
        )

        # Update Withdrawal status
        withdrawal.status = target_status
        withdrawal.failure_reason = failure_reason
        withdrawal.version += 1
        await session.flush()

        # Send notification
        await NotificationService.send_notification(
            session=session,
            user_id=withdrawal.user_id,
            notification_type="WITHDRAWAL_FAILED",
            message=f"Withdrawal request of {refund_amount} failed and funds were refunded to your balance. Reason: {failure_reason}."
        )

        return withdrawal
        
    @staticmethod
    async def complete_withdrawal(
        session: AsyncSession,
        withdrawal_id: uuid.UUID
    ) -> WithdrawalRequest:
        """Marks withdrawal request status as COMPLETED."""
        withdrawal_repo = WithdrawalRepository(session)
        withdrawal = await withdrawal_repo.get_by_id(withdrawal_id)
        if not withdrawal:
            raise EntityNotFoundException(f"Withdrawal request {withdrawal_id} not found")

        if withdrawal.status != WithdrawalStatus.PENDING and withdrawal.status != WithdrawalStatus.PROCESSING:
            return withdrawal  # Already finalized

        withdrawal.status = WithdrawalStatus.COMPLETED
        withdrawal.version += 1
        await session.flush()

        # Record double-entry completion entry (Internal liability mapping)
        # In a real treasury, this represents transferring matching funds from our payout reserve bank to user's external account.
        
        await NotificationService.send_notification(
            session=session,
            user_id=withdrawal.user_id,
            notification_type="WITHDRAWAL_COMPLETED",
            message=f"Withdrawal request of {withdrawal.amount} {withdrawal.currency} completed successfully."
        )
        
        return withdrawal
