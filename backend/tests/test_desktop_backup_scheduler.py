from datetime import timezone

from app import main
from app.services.desktop_backup_scheduler import DesktopBackupScheduler


class FakeBackgroundScheduler:
    def __init__(self):
        self.added_jobs = []
        self.started = 0
        self.shutdown_wait_values = []

    def add_job(self, func, trigger, **kwargs):
        self.added_jobs.append((func, trigger, kwargs))

    def start(self):
        self.started += 1

    def shutdown(self, wait=True):
        self.shutdown_wait_values.append(wait)


class TrackedSession:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_scheduler_submits_an_immediate_non_overlapping_hourly_due_check_and_closes_session():
    """A duplicated or blocking job could copy the database twice or retain a worker session."""
    backend = FakeBackgroundScheduler()
    sessions = []
    received_sessions = []

    class RecordingService:
        def run_if_due(self, db):
            received_sessions.append(db)

    scheduler = DesktopBackupScheduler(
        scheduler=backend,
        session_factory=lambda: sessions.append(TrackedSession()) or sessions[-1],
        service_factory=RecordingService,
    )

    scheduler.start()
    scheduler.run_scheduled_backup()
    scheduler.shutdown()

    assert backend.started == 1
    assert len(backend.added_jobs) == 1
    _, trigger, options = backend.added_jobs[0]
    assert trigger == "interval"
    assert options["hours"] == 1
    assert options["id"] == "desktop_automatic_backup_due_check"
    assert options["replace_existing"] is True
    assert options["max_instances"] == 1
    assert options["next_run_time"].tzinfo == timezone.utc
    assert received_sessions == sessions
    assert sessions[0].closed is True
    assert backend.shutdown_wait_values == [False]


def test_lifecycle_starts_and_stops_desktop_backup_only_in_desktop_mode(monkeypatch):
    """Starting the desktop writer in a browser deployment would create unexpected local files."""
    calls = []
    monkeypatch.setattr(main, "prepare_desktop_startup", lambda *_: calls.append("prepare"))
    monkeypatch.setattr(main, "init_db", lambda: calls.append("init"))
    monkeypatch.setattr(main.desktop_backup_scheduler, "start", lambda: calls.append("backup_start"))
    monkeypatch.setattr(main.desktop_backup_scheduler, "shutdown", lambda: calls.append("backup_stop"))
    monkeypatch.setattr(main.market_sync_scheduler, "start", lambda: calls.append("market_start"))
    monkeypatch.setattr(main.market_sync_scheduler, "shutdown", lambda: calls.append("market_stop"))
    monkeypatch.setenv("SELLHELP_DISABLE_MARKET_SYNC_SCHEDULER", "1")

    monkeypatch.setattr(main, "is_desktop_mode", lambda: True)
    main.initialize_database()
    main.shutdown_runtime_services()

    assert calls == ["prepare", "init", "backup_start", "backup_stop", "market_stop"]

    calls.clear()
    monkeypatch.setattr(main, "is_desktop_mode", lambda: False)
    main.initialize_database()
    main.shutdown_runtime_services()

    assert calls == ["init", "market_stop"]
