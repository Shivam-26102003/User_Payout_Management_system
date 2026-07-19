import asyncio
import structlog
from app.core.database import engine, Base
from seed import seed_data

logger = structlog.get_logger()

async def reset_database():
    logger.info("Connecting to database...")
    async with engine.begin() as conn:
        logger.info("Dropping all existing tables...")
        await conn.run_sync(Base.metadata.drop_all)
        
        logger.info("Recreating all database tables...")
        await conn.run_sync(Base.metadata.create_all)
        
    logger.info("Seeding initial demo data (users, brands, and sales)...")
    await seed_data()
    logger.info("Database reset and seeded successfully!")

if __name__ == "__main__":
    asyncio.run(reset_database())
