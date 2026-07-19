from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.brand import Brand
from app.repositories.base import BaseRepository

class BrandRepository(BaseRepository[Brand]):
    def __init__(self, session: AsyncSession):
        super().__init__(Brand, session)

    async def get_by_name(self, name: str) -> Brand | None:
        result = await self.session.execute(
            select(Brand).where(Brand.name == name, Brand.deleted_at.is_(None))
        )
        return result.scalars().first()
