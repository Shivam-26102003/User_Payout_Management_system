import asyncio
from datetime import datetime
import structlog
from sqlalchemy import update
from app.core.database import async_session_factory
from app.models.job import SystemJob
from app.repositories.job import JobRepository
from app.repositories.idempotency import IdempotencyRepository
from app.services.advance_payout_service import AdvancePayoutService

logger = structlog.get_logger()

async def acquire_job_lock(job_name: str) -> bool:
    """Attempts to lock a background job by updating its status to RUNNING in system_jobs."""
    async with async_session_factory() as session:
        repo = JobRepository(session)
        job = await repo.get_by_name(job_name)
        
        if not job:
            job = SystemJob(
                job_name=job_name,
                status="IDLE",
                last_run_at=None
            )
            session.add(job)
            await session.commit()
            
        # Try to atomically transition status from IDLE/FAILED to RUNNING
        from sqlalchemy import and_, or_
        stmt = (
            update(SystemJob)
            .where(
                and_(
                    SystemJob.job_name == job_name,
                    or_(
                        SystemJob.status == "IDLE",
                        SystemJob.status == "FAILED"
                    )
                )
            )
            .values(status="RUNNING", last_run_at=datetime.utcnow())
        )
        
        result = await session.execute(stmt)
        await session.commit()
        
        # If rowcount is 1, we successfully acquired the lock
        return result.rowcount == 1

async def release_job_lock(job_name: str, success: bool, error_log: str | None = None) -> None:
    """Releases the lock, updating status back to IDLE or FAILED."""
    async with async_session_factory() as session:
        stmt = (
            update(SystemJob)
            .where(SystemJob.job_name == job_name)
            .values(
                status="IDLE" if success else "FAILED",
                error_log=error_log if not success else None
            )
        )
        await session.execute(stmt)
        await session.commit()

# --- Job Declarations ---

async def run_advance_payout_job() -> None:
    job_name = "AdvancePayoutJob"
    if not await acquire_job_lock(job_name):
        return  # Job already running

    logger.info("Executing periodic job: AdvancePayoutJob")
    success = False
    error_msg = None
    try:
        async with async_session_factory() as session:
            await AdvancePayoutService.process_eligible_advance_payouts(session)
            await session.commit()
        success = True
    except Exception as e:
        logger.error("Error running AdvancePayoutJob", error=str(e))
        error_msg = str(e)
    finally:
        await release_job_lock(job_name, success, error_msg)

async def run_cleanup_idempotency_job() -> None:
    job_name = "CleanupIdempotencyJob"
    if not await acquire_job_lock(job_name):
        return

    logger.info("Executing periodic job: CleanupIdempotencyJob")
    success = False
    error_msg = None
    try:
        async with async_session_factory() as session:
            repo = IdempotencyRepository(session)
            deleted_count = await repo.delete_expired_keys()
            await session.commit()
            if deleted_count > 0:
                logger.info("Pruned expired idempotency keys", count=deleted_count)
        success = True
    except Exception as e:
        logger.error("Error running CleanupIdempotencyJob", error=str(e))
        error_msg = str(e)
    finally:
        await release_job_lock(job_name, success, error_msg)

async def run_retry_failed_withdrawal_job() -> None:
    # A stub for simulating payout gateway recoveries/retries
    job_name = "RetryFailedWithdrawalJob"
    if not await acquire_job_lock(job_name):
         return
    await release_job_lock(job_name, True)

async def run_notification_job() -> None:
    job_name = "NotificationJob"
    if not await acquire_job_lock(job_name):
         return
    await release_job_lock(job_name, True)

async def run_metrics_aggregation_job() -> None:
    job_name = "MetricsAggregationJob"
    if not await acquire_job_lock(job_name):
         return
    await release_job_lock(job_name, True)

async def run_auto_approval_job() -> None:
    job_name = "AutoApprovalJob"
    if not await acquire_job_lock(job_name):
        return

    logger.info("Executing periodic job: AutoApprovalJob")
    success = False
    error_msg = None
    try:
        async with async_session_factory() as session:
            from app.services.reconciliation_service import ReconciliationService
            await ReconciliationService.run_auto_approval_job(session)
            await session.commit()
        success = True
    except Exception as e:
        logger.error("Error running AutoApprovalJob", error=str(e))
        error_msg = str(e)
    finally:
        await release_job_lock(job_name, success, error_msg)

# --- Scheduler Loop ---

async def start_periodic_scheduler() -> None:
    """Runs a loop executing jobs at structured intervals sequentially to prevent SQLite lockups."""
    logger.info("Starting background scheduler loop...")
    while True:
        try:
            await run_advance_payout_job()
            await run_cleanup_idempotency_job()
            await run_retry_failed_withdrawal_job()
            await run_notification_job()
            await run_metrics_aggregation_job()
            await run_auto_approval_job()
        except Exception as e:
            logger.error("Error in scheduler loop", error=str(e))
            
        # Run loop every 10 seconds for fast reactive demonstrations/testing
        await asyncio.sleep(10)
