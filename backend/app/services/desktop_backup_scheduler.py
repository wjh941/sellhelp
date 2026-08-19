"""Background scheduling for local desktop automatic backups."""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.services.desktop_backup_service import DesktopBackupService


logger = logging.getLogger(__name__)
JOB_ID = "desktop_automatic_backup_due_check"


class DesktopBackupScheduler:
    def __init__(self, scheduler=None, session_factory=SessionLocal, service_factory=DesktopBackupService.for_active_database):
        self.scheduler = scheduler or BackgroundScheduler(timezone="Asia/Shanghai")
        self.session_factory = session_factory
        self.service_factory = service_factory
        self._started = False

    def start(self):
        if self._started:
            return
        self.scheduler.add_job(
            self.run_scheduled_backup,
            "interval",
            hours=1,
            id=JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            next_run_time=datetime.now(timezone.utc),
        )
        self.scheduler.start()
        self._started = True

    def shutdown(self):
        if self._started:
            self.scheduler.shutdown(wait=False)
            self._started = False

    def run_scheduled_backup(self):
        db = self.session_factory()
        try:
            self.service_factory().run_if_due(db)
        except Exception as exc:
            logger.error("Desktop automatic backup scheduler failed: %s", type(exc).__name__)
        finally:
            db.close()


desktop_backup_scheduler = DesktopBackupScheduler()
