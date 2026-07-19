import pytest
import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.balance import Balance
from app.domain.enums import UserRole, UserStatus, WithdrawalStatus
from app.services.withdrawal_service import WithdrawalService
from app.services.balance_service import BalanceService
from app.domain.value_objects.money import Money
from app.domain.exceptions import CooldownActiveException, InsufficientFundsException

@pytest.fixture
async def setup_user(db_session: AsyncSession):
    user = User(
        email="payout_user@example.com",
        password_hash="pass",
        name="John Doe",
        role=UserRole.USER,
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    await db_session.flush()
    
    balance = Balance(user_id=user.id, withdrawable_balance=Decimal("100.0000"))
    db_session.add(balance)
    await db_session.commit()
    return user

@pytest.mark.asyncio
async def test_withdrawal_cooldown_and_recovery(db_session: AsyncSession, setup_user):
    user = setup_user

    # 1. First withdrawal of 40 INR
    w1 = await WithdrawalService.request_withdrawal(
        session=db_session,
        user_id=user.id,
        amount=Money("40.0000")
    )
    assert w1.status == WithdrawalStatus.PENDING
    
    # Balance should be 100 - 40 = 60
    balance = await BalanceService.get_or_create_balance(db_session, user.id)
    assert balance.withdrawable_balance == Decimal("60.0000")

    # 2. Second withdrawal immediately (must fail due to cooldown)
    with pytest.raises(CooldownActiveException):
        await WithdrawalService.request_withdrawal(
            session=db_session,
            user_id=user.id,
            amount=Money("10.0000")
        )

    # 3. Third withdrawal exceeds funds (would fail anyway, but cooldown checks first; if we simulate resolving w1 as failed...)
    # 4. Resolve w1 as FAILED (triggers recovery payout refund)
    w_recovered = await WithdrawalService.process_withdrawal_recovery(
        session=db_session,
        withdrawal_id=w1.id,
        target_status=WithdrawalStatus.FAILED,
        failure_reason="Gateway API Timeout"
    )
    assert w_recovered.status == WithdrawalStatus.FAILED

    # Balance should be restored to 60 + 40 = 100
    await db_session.refresh(balance)
    assert balance.withdrawable_balance == Decimal("100.0000")

    # 5. Since withdrawal failed, user should be allowed to withdraw again immediately (cooldown bypassed)
    w2 = await WithdrawalService.request_withdrawal(
        session=db_session,
        user_id=user.id,
        amount=Money("100.0000")
    )
    assert w2.status == WithdrawalStatus.PENDING
    
    # Balance should be 0
    await db_session.refresh(balance)
    assert balance.withdrawable_balance == Decimal("0.0000")
