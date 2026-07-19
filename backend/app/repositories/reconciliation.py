from sqlalchemy.ext.asyncio import AsyncSession
from app.models.reconciliation import ReconciliationJob
from app.repositories.base import BaseRepository

class ReconciliationRepository(BaseRepository[ReconciliationJob]):
    def __init__(self, session: AsyncSession):
        super().__init__(ReconciliationJob, session)
