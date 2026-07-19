import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.brand import Brand
from app.models.sale import Sale
from app.models.balance import Balance
from app.models.ledger import LedgerTransaction
from app.models.advance_payout import AdvancePayout
from app.domain.enums import UserRole, UserStatus, SaleStatus, AdvanceStatus
from app.services.advance_payout_service import AdvancePayoutService
from app.services.reconciliation_service import ReconciliationService
from app.services.balance_service import BalanceService

@pytest.fixture
async def setup_test_entities(db_session: AsyncSession):
    # Setup standard entities
    user = User(
        email="test_affiliate@example.com",
        password_hash="hashedpass",
        name="Affiliate Test",
        role=UserRole.USER,
        status=UserStatus.ACTIVE
    )
    admin = User(
        email="admin_reconciler@example.com",
        password_hash="hashedpass",
        name="Admin Test",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE
    )
    db_session.add_all([user, admin])
    await db_session.flush()

    # Setup Balance Cache
    user_balance = Balance(user_id=user.id, withdrawable_balance=Decimal("0.0000"))
    db_session.add(user_balance)

    brand = Brand(name="test_brand")
    db_session.add(brand)
    await db_session.flush()

    return {"user": user, "admin": admin, "brand": brand}

@pytest.mark.asyncio
async def test_advance_payout_and_reconciliation_flow(db_session: AsyncSession, setup_test_entities):
    entities = setup_test_entities
    user = entities["user"]
    admin = entities["admin"]
    brand = entities["brand"]

    # 1. Create a sale matching PDF Case 1: Earning = 30
    sale_case1 = Sale(
        user_id=user.id,
        brand_id=brand.id,
        external_id="sale_case1",
        amount=Decimal("300.0000"),
        earnings=Decimal("30.0000"), # 30 INR earnings
        status=SaleStatus.PENDING,
        advance_status=AdvanceStatus.PENDING
    )
    db_session.add(sale_case1)
    await db_session.commit()

    # 2. Run Advance Payout Job
    results = await AdvancePayoutService.process_eligible_advance_payouts(db_session)
    assert len(results) == 1
    assert results[0]["status"] == "SUCCESS"
    assert Decimal(results[0]["advance_paid"]) == Decimal("3.0000") # 10% of 30 is 3

    # Verify user's balance cache contains the advance payout
    balance = await BalanceService.get_or_create_balance(db_session, user.id)
    assert balance.withdrawable_balance == Decimal("3.0000")

    # Verify advance status is PAID
    await db_session.refresh(sale_case1)
    assert sale_case1.advance_status == AdvanceStatus.PAID

    # Try running advance job again (must skip as already paid)
    retry_results = await AdvancePayoutService.process_eligible_advance_payouts(db_session)
    assert len(retry_results) == 0

    # 3. Reconcile as APPROVED (Case 1)
    # Remaining = 30 - 3 = 27
    reconcile_reqs = [{"sale_id": sale_case1.id, "action": "APPROVED"}]
    job = await ReconciliationService.reconcile_sales(db_session, admin.id, reconcile_reqs)
    assert job.status == "COMPLETED"

    # Verify user's balance is updated to 3 + 27 = 30
    await db_session.refresh(balance)
    assert balance.withdrawable_balance == Decimal("30.0000")

    # Verify Ledger contains double-entries for both movements
    # 2 entries for advance (+3 user, -3 reserve)
    # 2 entries for sale approved (+27 user, -27 reserve)
    ledger_query = select(LedgerTransaction).where(LedgerTransaction.user_id == user.id)
    ledger_res = await db_session.execute(ledger_query)
    ledger_entries = ledger_res.scalars().all()
    assert len(ledger_entries) == 2  # User entries: 1 for advance, 1 for approval
    
    # 4. Test Case 2: Rejected Sale
    # Create sale earning = 50
    sale_case2 = Sale(
        user_id=user.id,
        brand_id=brand.id,
        external_id="sale_case2",
        amount=Decimal("500.0000"),
        earnings=Decimal("50.0000"),
        status=SaleStatus.PENDING,
        advance_status=AdvanceStatus.PENDING
    )
    db_session.add(sale_case2)
    await db_session.commit()

    # Process Advance payout: 10% of 50 = 5
    await AdvancePayoutService.process_eligible_advance_payouts(db_session)
    await db_session.refresh(balance)
    assert balance.withdrawable_balance == Decimal("35.0000") # 30 + 5 = 35

    # Reconcile as REJECTED (Case 2)
    # Adjustment = -5
    reconcile_reqs_reject = [{"sale_id": sale_case2.id, "action": "REJECTED"}]
    job_reject = await ReconciliationService.reconcile_sales(db_session, admin.id, reconcile_reqs_reject)
    assert job_reject.status == "COMPLETED"

    # Verify user's balance is updated to 35 - 5 = 30
    await db_session.refresh(balance)
    assert balance.withdrawable_balance == Decimal("30.0000")
