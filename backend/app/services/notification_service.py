import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import NotificationLog

logger = structlog.get_logger()

class NotificationService:
    @staticmethod
    async def send_notification(
        session: AsyncSession,
        user_id: uuid.UUID,
        notification_type: str,
        message: str
    ) -> NotificationLog:
        """Logs notification details to database and prints dispatch simulation log."""
        log = NotificationLog(
            user_id=user_id,
            notification_type=notification_type,
            channel="EMAIL",
            status="SENT",
            message=message
        )
        session.add(log)
        await session.flush()

        logger.info(
            "Notification Dispatched",
            user_id=str(user_id),
            type=notification_type,
            message=message
        )
        return log
