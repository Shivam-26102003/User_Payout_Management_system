import uuid
import structlog
from decimal import Decimal
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.advance_payout import AdvancePayout
from app.models.sale import Sale
from app.repositories.sale import SaleRepository
from app.repositories.balance import BalanceRepository
from app.services.ledger_service import LedgerService
from app.services.balance_service import BalanceService
from app.services.notification_service import NotificationService
from app.domain.enums import SaleStatus, AdvanceStatus, LedgerTransactionType
from app.domain.value_objects.money import Money

logger = structlog.get_logger()

class AdvancePayoutService:
    @staticmethod
    async def process_sale_advance(session: AsyncSession, sale: Sale) -> Dict[str, Any]:
        """Processes and credits the 10% advance payout for a single sale, adjusting user balances and writing ledger records."""
        # Calculate 10% advance
        earnings = Money(sale.earnings)
        advance_amount = earnings.multiply(Decimal("0.10"))
        
        if advance_amount.amount <= Decimal("0.00"):
            # If 10% is zero, skip advance payout creation but mark as skipped
            sale.advance_status = AdvanceStatus.SKIPPED
            await session.flush()
            return {
                "sale_id": str(sale.id),
                "status": "SKIPPED",
                "reason": "Advance payout amount is zero"
            }

        # Lock User's balance row (Pessimistic Lock)
        balance_repo = BalanceRepository(session)
        await balance_repo.get_by_user_id_for_update(sale.user_id)
        
        # Create AdvancePayout record
        payout = AdvancePayout(
            sale_id=sale.id,
            user_id=sale.user_id,
            amount=advance_amount.amount,
            status="COMPLETED"
        )
        session.add(payout)
        await session.flush()

        # Write double-entry Ledger transactions
        # Credit User Balance (+Advance), Debit Corporate Advance Reserve (-Advance)
        tx_group_id = await LedgerService.record_transaction(
            session=session,
            user_id=sale.user_id,
            amount=advance_amount,
            transaction_type=LedgerTransactionType.ADVANCE_PAYOUT,
            reference_type="ADVANCE_PAYOUT",
            reference_id=payout.id
        )

        # Update user's balance cache
        await BalanceService.adjust_balance(
            session=session,
            user_id=sale.user_id,
            amount=advance_amount
        )

        # Update Sale advance status to PAID
        sale.advance_status = AdvanceStatus.PAID
        sale.version += 1
        await session.flush()

        # Dispatch notification
        await NotificationService.send_notification(
            session=session,
            user_id=sale.user_id,
            notification_type="ADVANCE_PAYOUT_RECEIVED",
            message=f"You received an advance payout of {advance_amount} on pending sale {sale.external_id}."
        )
        
        return {
            "sale_id": str(sale.id),
            "status": "SUCCESS",
            "advance_paid": str(advance_amount.amount),
            "transaction_group_id": str(tx_group_id)
        }

    @staticmethod
    async def process_eligible_advance_payouts(session: AsyncSession) -> List[Dict[str, Any]]:
        """
        Scans for pending sales, locks balances, and credits 10% advance payouts.
        Each sale runs within a database savepoint boundary to isolate failures.
        """
        sale_repo = SaleRepository(session)
        eligible_sales = await sale_repo.get_sales_for_advance_payout()
        
        results = []
        
        for sale in eligible_sales:
            # Skip if status is not Pending or advance is already paid/skipped
            if sale.status != SaleStatus.PENDING or sale.advance_status != AdvanceStatus.PENDING:
                continue

            try:
                # Use a nested transaction savepoint to isolate this sale's operations
                async with session.begin_nested():
                    res = await AdvancePayoutService.process_sale_advance(session, sale)
                    results.append(res)
                    
                # Commit the savepoint if successful
                await session.commit()
                
            except Exception as e:
                logger.error(
                    "Failed to process advance payout for sale",
                    sale_id=str(sale.id),
                    error=str(e)
                )
                # Rollback to the savepoint for this specific sale
                await session.rollback()
                results.append({
                    "sale_id": str(sale.id),
                    "status": "FAILED",
                    "reason": str(e)
                })

        return results
