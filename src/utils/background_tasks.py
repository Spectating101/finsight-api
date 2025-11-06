"""
Background Tasks for FinSight API
Periodic maintenance tasks
"""

import asyncio
import structlog
from datetime import datetime, timedelta
import asyncpg

logger = structlog.get_logger(__name__)


class BackgroundTaskManager:
    """Manages background tasks for the application"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.tasks = []
        self._shutdown = False

    async def start(self):
        """Start all background tasks"""
        logger.info("Starting background tasks")

        # Start monthly usage reset task
        task = asyncio.create_task(self._monthly_usage_reset_task())
        self.tasks.append(task)

        logger.info("Background tasks started", task_count=len(self.tasks))

    async def stop(self):
        """Stop all background tasks"""
        logger.info("Stopping background tasks")
        self._shutdown = True

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for all tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("Background tasks stopped")

    async def _monthly_usage_reset_task(self):
        """
        Check daily if monthly usage needs to be reset
        Runs every 24 hours at midnight UTC
        """
        logger.info("Monthly usage reset task started")

        while not self._shutdown:
            try:
                # Calculate next midnight UTC
                now = datetime.utcnow()
                tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                sleep_seconds = (tomorrow - now).total_seconds()

                # Wait until midnight
                logger.info(
                    "Next usage reset check scheduled",
                    next_run=tomorrow.isoformat(),
                    sleep_seconds=sleep_seconds
                )
                await asyncio.sleep(sleep_seconds)

                if self._shutdown:
                    break

                # Check if it's the 1st of the month
                now = datetime.utcnow()
                if now.day == 1:
                    logger.info("First of month detected, resetting monthly usage")
                    await self._reset_monthly_usage()
                else:
                    logger.debug("Not first of month, skipping reset", day=now.day)

            except asyncio.CancelledError:
                logger.info("Monthly usage reset task cancelled")
                break
            except Exception as e:
                logger.error(
                    "Error in monthly usage reset task",
                    error=str(e),
                    exc_info=True
                )
                # Sleep for an hour before retrying
                await asyncio.sleep(3600)

    async def _reset_monthly_usage(self):
        """
        Reset monthly API call counters for all users
        Calls the database function reset_monthly_usage()
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Call the SQL function
                result = await conn.fetchval("SELECT reset_monthly_usage()")

                logger.info(
                    "Monthly usage reset completed",
                    users_reset=result,
                    timestamp=datetime.utcnow().isoformat()
                )

                # Log to subscription_history for audit trail
                await conn.execute(
                    """
                    INSERT INTO subscription_history
                        (user_id, event_type, new_tier, metadata)
                    SELECT
                        user_id,
                        'usage_reset',
                        tier,
                        jsonb_build_object(
                            'reset_at', $1,
                            'automated', true
                        )
                    FROM users
                    WHERE status = 'active'
                    """,
                    datetime.utcnow()
                )

                logger.info("Audit trail created for usage reset")

        except Exception as e:
            logger.error(
                "Failed to reset monthly usage",
                error=str(e),
                exc_info=True
            )
            raise
