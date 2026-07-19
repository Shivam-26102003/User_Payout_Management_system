from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.job import SystemJob
from app.repositories.base import BaseRepository

class JobRepository(BaseRepository[SystemJob]):
    def __init__(self, session: AsyncSession):
        super().__init__(SystemJob, session)

    async def get_by_name(self, job_name: str) -> SystemJob | None:
        result = await self.session.execute(
            select(SystemJob).where(SystemJob.job_name == job_name)
        )
        return result.scalars().first()
