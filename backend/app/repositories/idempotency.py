from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.idempotency import IdempotencyKey
from app.repositories.base import BaseRepository

class IdempotencyRepository(BaseRepository[IdempotencyKey]):
    def __init__(self, session: AsyncSession):
        super().__init__(IdempotencyKey, session)

    async def get_by_key(self, key: str) -> IdempotencyKey | None:
        """Fetch idempotency key from DB, filtering out expired ones."""
        result = await self.session.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.key == key,
                IdempotencyKey.expires_at > datetime.utcnow()
            )
        )
        return result.scalars().first()

    async def create_key(
        self,
        key: str,
        response_status: int,
        response_body: dict,
        expires_in_seconds: int = 86400  # Default 24 hours
    ) -> IdempotencyKey:
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
        entry = IdempotencyKey(
            key=key,
            response_status=response_status,
            response_body=response_body,
            expires_at=expires_at
        )
        self.session.add(entry)
        await self.session.flush()
        return entry
        
    async def delete_expired_keys(self) -> int:
        from sqlalchemy import delete
        now = datetime.utcnow()
        result = await self.session.execute(
            delete(IdempotencyKey).where(IdempotencyKey.expires_at <= now)
        )
        return result.rowcount
