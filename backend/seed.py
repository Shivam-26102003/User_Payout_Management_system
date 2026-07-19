import asyncio
from decimal import Decimal
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import engine, Base, async_session_factory
from app.core.security import get_password_hash
from app.models.user import User
from app.models.brand import Brand
from app.models.sale import Sale
from app.models.balance import Balance
from app.domain.enums import UserRole, UserStatus, SaleStatus, AdvanceStatus

logger = structlog.get_logger()

async def create_tables():
    """Drops (optional) and creates all database tables."""
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        # For a clean slate in docker-compose, we can recreate tables
        # Base.metadata.drop_all(conn)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized successfully.")

async def seed_data():
    """Seeds default admin, affiliate, brands, and sales for demonstration."""
    async with async_session_factory() as session:
        # Check if users already exist
        result = await session.execute(select(User).limit(1))
        if result.scalars().first():
            logger.info("Database already seeded. Skipping seeder.")
            return

        logger.info("Seeding database...")

        # 1. Create Users
        admin_pass = get_password_hash("adminpassword")
        user_pass = get_password_hash("userpassword")
        viewer_pass = get_password_hash("viewerpassword")

        admin = User(
            email="admin@example.com",
            password_hash=admin_pass,
            name="Platform Administrator",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE
        )
        affiliate = User(
            email="affiliate@example.com",
            password_hash=user_pass,
            name="John Doe",
            role=UserRole.USER,
            status=UserStatus.ACTIVE
        )
        viewer = User(
            email="viewer@example.com",
            password_hash=viewer_pass,
            name="Guest Auditor",
            role=UserRole.VIEWER,
            status=UserStatus.ACTIVE
        )

        session.add_all([admin, affiliate, viewer])
        await session.flush()

        # Create Balance row for each user
        admin_balance = Balance(user_id=admin.id, withdrawable_balance=Decimal("0.0000"))
        affiliate_balance = Balance(user_id=affiliate.id, withdrawable_balance=Decimal("0.0000"))
        viewer_balance = Balance(user_id=viewer.id, withdrawable_balance=Decimal("0.0000"))
        session.add_all([admin_balance, affiliate_balance, viewer_balance])

        # 2. Create Brands
        b1 = Brand(name="brand_1")
        b2 = Brand(name="brand_2")
        b3 = Brand(name="brand_3")
        session.add_all([b1, b2, b3])
        await session.flush()

        # 3. Create Sales (Example cases matching the assignment spec)
        
        # Example 1: Three pending sales of 40 earnings each (Total pending = 120, advance = 12)
        s1 = Sale(
            user_id=affiliate.id,
            brand_id=b1.id,
            external_id="sale_001",
            amount=Decimal("400.0000"),
            earnings=Decimal("40.0000"),
            status=SaleStatus.PENDING,
            advance_status=AdvanceStatus.PENDING
        )
        s2 = Sale(
            user_id=affiliate.id,
            brand_id=b1.id,
            external_id="sale_002",
            amount=Decimal("400.0000"),
            earnings=Decimal("40.0000"),
            status=SaleStatus.PENDING,
            advance_status=AdvanceStatus.PENDING
        )
        s3 = Sale(
            user_id=affiliate.id,
            brand_id=b1.id,
            external_id="sale_003",
            amount=Decimal("400.0000"),
            earnings=Decimal("40.0000"),
            status=SaleStatus.PENDING,
            advance_status=AdvanceStatus.PENDING
        )

        # Example Case 1: Sale of earnings = 30 (Approved, advance paid = 3 -> final adjustment = 27)
        s4 = Sale(
            user_id=affiliate.id,
            brand_id=b2.id,
            external_id="sale_case_1",
            amount=Decimal("300.0000"),
            earnings=Decimal("30.0000"),
            status=SaleStatus.PENDING,
            advance_status=AdvanceStatus.PENDING
        )

        # Example Case 2: Sale of earnings = 50 (Rejected, advance paid = 5 -> final adjustment = -5)
        s5 = Sale(
            user_id=affiliate.id,
            brand_id=b3.id,
            external_id="sale_case_2",
            amount=Decimal("500.0000"),
            earnings=Decimal("50.0000"),
            status=SaleStatus.PENDING,
            advance_status=AdvanceStatus.PENDING
        )

        session.add_all([s1, s2, s3, s4, s5])
        await session.commit()
        logger.info("Database seeding finished successfully.")

async def main():
    await create_tables()
    await seed_data()

if __name__ == "__main__":
    asyncio.run(main())
