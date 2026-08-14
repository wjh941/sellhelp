"""Daily scheduling for controlled external market-data synchronization."""

import logging
import re

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ..database import SessionLocal
from ..models.all_models import SystemConfig
from .market_sync_service import ExternalMarketSyncService


logger = logging.getLogger(__name__)
SYNC_TIME_KEY = "external_market_sync_time"
DEFAULT_SYNC_TIME = "02:00"
JOB_ID = "external_market_sync_daily"
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class MarketSyncScheduler:
    def __init__(self, scheduler=None, session_factory=SessionLocal, service_factory=ExternalMarketSyncService):
        self.scheduler = scheduler or BackgroundScheduler(timezone="Asia/Shanghai")
        self.session_factory = session_factory
        self.service_factory = service_factory
        self._started = False

    def start(self):
        self.reschedule()
        if not self._started:
            self.scheduler.start()
            self._started = True

    def shutdown(self):
        if self._started:
            self.scheduler.shutdown(wait=False)
            self._started = False

    def reschedule(self, sync_time=None):
        sync_time = sync_time or self._stored_sync_time()
        hour, minute = self._parse_time(sync_time)
        self.scheduler.add_job(
            self.run_scheduled_sync,
            CronTrigger(hour=hour, minute=minute, timezone="Asia/Shanghai"),
            id=JOB_ID,
            replace_existing=True,
        )

    def _stored_sync_time(self):
        db = self.session_factory()
        try:
            schedule = db.query(SystemConfig).filter(SystemConfig.key == SYNC_TIME_KEY).first()
            return schedule.value if schedule else DEFAULT_SYNC_TIME
        finally:
            db.close()

    @staticmethod
    def _parse_time(sync_time):
        if not isinstance(sync_time, str) or not TIME_PATTERN.fullmatch(sync_time):
            raise ValueError("sync_time must use HH:MM in 24-hour time")
        hour, minute = sync_time.split(":")
        return int(hour), int(minute)

    def run_scheduled_sync(self):
        db = self.session_factory()
        try:
            self.service_factory(db).sync(trigger="scheduled")
        except Exception as exc:
            logger.error("Scheduled external market sync failed: %s", type(exc).__name__)
        finally:
            db.close()


market_sync_scheduler = MarketSyncScheduler()


def get_market_sync_scheduler():
    return market_sync_scheduler
