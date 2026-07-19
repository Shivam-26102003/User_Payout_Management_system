import uuid
import structlog
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.reconciliation import ReconciliationJob
from app.models.advance_payout import AdvancePayout
from app.repositories.sale import SaleRepository
from app.repositories.balance import BalanceRepository
from app.repositories.reconciliation import ReconciliationRepository
from app.services.ledger_service import LedgerService
from app.services.balance_service import BalanceService
from app.services.notification_service import NotificationService
from app.domain.enums import SaleStatus, AdvanceStatus, LedgerTransactionType
from app.domain.value_objects.money import Money
from app.domain.exceptions import EntityNotFoundException, InvalidSaleStatusException

logger = structlog.get_logger()

class ReconciliationService:
    @staticmethod
    async def reconcile_sales(
        session: AsyncSession,
        admin_id: uuid.UUID,
        requests: List[Dict[str, Any]]
    ) -> ReconciliationJob:
        """
        Processes bulk approvals or rejections of sales.
        Adjusts user balances and records balanced double-entry ledger entries.
        """
        # Create Reconciliation Job Tracker
        job_repo = ReconciliationRepository(session)
        job = ReconciliationJob(
            admin_id=admin_id,
            status="RUNNING"
        )
        await job_repo.create(job)
        await session.commit()

        success_count = 0
        failure_count = 0
        error_details = []

        sale_repo = SaleRepository(session)
        balance_repo = BalanceRepository(session)

        for req in requests:
            sale_id = uuid.UUID(req["sale_id"]) if isinstance(req["sale_id"], str) else req["sale_id"]
            action = req["action"].upper()  # APPROVED or REJECTED

            try:
                # Use a nested transaction savepoint to isolate this sale's operations
                async with session.begin_nested():
                    # 1. Fetch sale
                    sale = await sale_repo.get_by_id(sale_id)
                    if not sale:
                        raise EntityNotFoundException(f"Sale {sale_id} not found")

                    if sale.status != SaleStatus.PENDING:
                        raise InvalidSaleStatusException(
                            f"Sale {sale_id} is already in state {sale.status} and cannot be reconciled"
                        )

                    # 2. Lock User's balance row (Pessimistic Lock)
                    await balance_repo.get_by_user_id_for_update(sale.user_id)

                    # 3. Check if there was an advance payout paid
                    advance_query = select(AdvancePayout).where(
                        AdvancePayout.sale_id == sale.id,
                        AdvancePayout.status == "COMPLETED"
                    )
                    advance_result = await session.execute(advance_query)
                    advance = advance_result.scalars().first()
                    
                    advance_paid = Money(advance.amount) if advance else Money("0.0000")
                    earnings = Money(sale.earnings)

                    if action == "APPROVED":
                        # Case 1: Approved Sale
                        # Remaining Payout = Earnings - Advance Paid
                        remaining_payout = earnings - advance_paid
                        
                        # Record double entry: Credit User withdrawable (+Remaining), Debit System (-Remaining)
                        tx_group_id = await LedgerService.record_transaction(
                            session=session,
                            user_id=sale.user_id,
                            amount=remaining_payout,
                            transaction_type=LedgerTransactionType.SALE_APPROVED,
                            reference_type="SALE",
                            reference_id=sale.id
                        )

                        # Adjust user balance cache
                        await BalanceService.adjust_balance(
                            session=session,
                            user_id=sale.user_id,
                            amount=remaining_payout
                        )

                        # Transition sale details
                        sale.status = SaleStatus.APPROVED
                        sale.reconciled_at = datetime.utcnow()
                        sale.reconciliation_job_id = job.id
                        sale.version += 1

                        await session.flush()

                        # Notify User
                        await NotificationService.send_notification(
                            session=session,
                            user_id=sale.user_id,
                            notification_type="SALE_APPROVED",
                            message=f"Sale {sale.external_id} approved. Remaining payout of {remaining_payout} credited."
                        )

                    elif action == "REJECTED":
                        # Case 2: Rejected Sale
                        # Adjustment = -Advance Paid
                        adjustment = Money("-0.0000") - advance_paid
                        
                        # Record double entry: Debit User withdrawable (-Advance), Credit System (+Advance)
                        tx_group_id = await LedgerService.record_transaction(
                            session=session,
                            user_id=sale.user_id,
                            amount=adjustment,
                            transaction_type=LedgerTransactionType.SALE_REJECTED,
                            reference_type="SALE",
                            reference_id=sale.id
                        )

                        # Adjust user balance cache (this may push balance to negative)
                        await BalanceService.adjust_balance(
                            session=session,
                            user_id=sale.user_id,
                            amount=adjustment
                        )

                        # Transition sale details
                        sale.status = SaleStatus.REJECTED
                        sale.reconciled_at = datetime.utcnow()
                        sale.reconciliation_job_id = job.id
                        sale.version += 1

                        await session.flush()

                        # Notify User
                        await NotificationService.send_notification(
                            session=session,
                            user_id=sale.user_id,
                            notification_type="SALE_REJECTED",
                            message=f"Sale {sale.external_id} rejected. Adjustment of {adjustment} applied to your balance."
                        )

                    else:
                        raise ValueError(f"Invalid reconciliation action: {action}")

                    success_count += 1
                
                # Commit the savepoint if successful
                await session.commit()

            except Exception as e:
                logger.error(
                    "Failed to reconcile sale in bulk job",
                    sale_id=str(sale_id),
                    error=str(e)
                )
                await session.rollback()
                failure_count += 1
                error_details.append(f"Sale {sale_id}: {str(e)}")

        # Update Job Status
        job.status = "COMPLETED" if failure_count == 0 else "FAILED"
        if error_details:
            job.error_details = "; ".join(error_details)
        
        await job_repo.update(job)
        await session.commit()

        return job

    @staticmethod
    async def run_auto_approval_job(session: AsyncSession) -> List[Dict[str, Any]]:
        """
        Admin/System job: Scans for PENDING sales older than 7 days, automatically approves them,
        credits the remaining commission (earnings - advance paid), and updates ledger + balances.
        """
        from datetime import datetime, timedelta
        from sqlalchemy import and_
        from app.models.sale import Sale
        from app.domain.enums import SaleStatus, AdvanceStatus, LedgerTransactionType
        from app.models.reconciliation import ReconciliationJob
        
        # 1. Query pending sales older than 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        query = select(Sale).where(
            and_(
                Sale.status == SaleStatus.PENDING,
                Sale.created_at <= seven_days_ago,
                Sale.deleted_at.is_(None)
            )
        )
        res = await session.execute(query)
        eligible_sales = res.scalars().all()
        
        if not eligible_sales:
            return []

        # Create a System Reconciliation Job tracker for logging
        job_repo = ReconciliationRepository(session)
        job = ReconciliationJob(
            admin_id=None,  # System-triggered
            status="RUNNING"
        )
        await job_repo.create(job)
        await session.flush()

        results = []
        balance_repo = BalanceRepository(session)
        
        for sale in eligible_sales:
            try:
                # Use nested savepoint to isolate each auto-approval operation
                async with session.begin_nested():
                    # Lock user balance
                    await balance_repo.get_by_user_id_for_update(sale.user_id)
                    
                    # Fetch advance payout if any
                    advance_query = select(AdvancePayout).where(
                        and_(
                            AdvancePayout.sale_id == sale.id,
                            AdvancePayout.status == "COMPLETED"
                        )
                    )
                    adv_res = await session.execute(advance_query)
                    advance = adv_res.scalars().first()
                    
                    advance_paid = Money(advance.amount) if advance else Money("0.0000")
                    earnings = Money(sale.earnings)
                    
                    # Credit remaining commission
                    remaining_payout = earnings - advance_paid
                    
                    # Record double entry ledger
                    tx_group_id = await LedgerService.record_transaction(
                        session=session,
                        user_id=sale.user_id,
                        amount=remaining_payout,
                        transaction_type=LedgerTransactionType.SALE_APPROVED,
                        reference_type="SALE",
                        reference_id=sale.id
                    )
                    
                    # Adjust user balance
                    await BalanceService.adjust_balance(
                        session=session,
                        user_id=sale.user_id,
                        amount=remaining_payout
                    )
                    
                    # Transition sale status
                    sale.status = SaleStatus.APPROVED
                    sale.reconciled_at = datetime.utcnow()
                    sale.reconciliation_job_id = job.id
                    sale.version += 1
                    await session.flush()
                    
                    # Dispatch notification
                    await NotificationService.send_notification(
                        session=session,
                        user_id=sale.user_id,
                        notification_type="SALE_APPROVED",
                        message=f"Sale {sale.external_id} was automatically approved after 7 days. Remaining payout of {remaining_payout} credited."
                    )
                    
                    results.append({
                        "sale_id": str(sale.id),
                        "status": "SUCCESS",
                        "credited_amount": str(remaining_payout.amount)
                    })
                # Commit nested savepoint
                await session.commit()
            except Exception as e:
                logger.error("Auto approval failed for sale", sale_id=str(sale.id), error=str(e))
                await session.rollback()
                results.append({
                    "sale_id": str(sale.id),
                    "status": "FAILED",
                    "reason": str(e)
                })

        job.status = "COMPLETED"
        await job_repo.update(job)
        await session.commit()
        return results
