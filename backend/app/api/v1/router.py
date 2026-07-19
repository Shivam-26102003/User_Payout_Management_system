from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    users,
    sales,
    advance_payouts,
    admin,
    withdrawals,
    ledger,
    balances,
    dashboard,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(sales.router, prefix="/sales", tags=["Sales"])
api_router.include_router(advance_payouts.router, prefix="/advance-payouts", tags=["Advance Payouts"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin Reconciliation"])
api_router.include_router(withdrawals.router, prefix="/withdrawals", tags=["Withdrawals"])
api_router.include_router(ledger.router, prefix="/ledger", tags=["Ledger Transactions"])
api_router.include_router(balances.router, prefix="/balances", tags=["Balances"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard Analytics"])
