from typing import List
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
from app.repositories.base import BaseRepository

class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(AuditLog, session)

    async def list_audit_logs(
        self,
        user_id: UUID | None = None,
        action: str | None = None,
        offset: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        query = select(AuditLog)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_total_audit_count(
        self,
        user_id: UUID | None = None,
        action: str | None = None
    ) -> int:
        query = select(func.count(AuditLog.id))
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        result = await self.session.execute(query)
        return result.scalar() or 0
