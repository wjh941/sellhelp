from datetime import timezone

from sqlalchemy.orm import sessionmaker

from app.models.all_models import SystemConfig


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


def test_start_uses_default_time_and_replaces_the_fixed_daily_job(db_session, monkeypatch):
    """Removing the default or replace flag would leave the daily sync unscheduled or duplicated."""
    from app.services.market_sync_scheduler import MarketSyncScheduler

    monkeypatch.setattr("apscheduler.triggers.cron.get_localzone", lambda: timezone.utc)
    scheduler_backend = FakeBackgroundScheduler()
    session_factory = sessionmaker(bind=db_session.get_bind())
    scheduler = MarketSyncScheduler(scheduler=scheduler_backend, session_factory=session_factory)

    scheduler.start()
    db_session.add(SystemConfig(key="external_market_sync_time", value="18:05"))
    db_session.commit()
    scheduler.reschedule()
    scheduler.shutdown()

    assert scheduler_backend.started == 1
    assert len(scheduler_backend.added_jobs) == 2
    assert scheduler_backend.shutdown_wait_values == [False]
    for _, trigger, kwargs in scheduler_backend.added_jobs:
        assert kwargs["id"] == "external_market_sync_daily"
        assert kwargs["replace_existing"] is True
        assert str(trigger) in {"cron[hour='2', minute='0']", "cron[hour='18', minute='5']"}
        assert str(trigger.timezone) == "Asia/Shanghai"


def test_reschedule_rejects_non_24_hour_time(db_session):
    """Accepting a malformed time would make a persisted schedule impossible to run."""
    import pytest

    from app.services.market_sync_scheduler import MarketSyncScheduler

    scheduler = MarketSyncScheduler(
        scheduler=FakeBackgroundScheduler(),
        session_factory=sessionmaker(bind=db_session.get_bind()),
    )

    with pytest.raises(ValueError, match="HH:MM"):
        scheduler.reschedule("24:00")


def test_scheduled_job_uses_a_fresh_session_calls_scheduled_sync_and_closes_it():
    """Reusing a request session or omitting the scheduled trigger would couple background work to HTTP state."""
    from app.services.market_sync_scheduler import MarketSyncScheduler

    class FreshSession:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    sessions = []

    def session_factory():
        session = FreshSession()
        sessions.append(session)
        return session

    calls = []

    class FakeSyncService:
        def __init__(self, db):
            calls.append(db)

        def sync(self, trigger):
            calls.append(trigger)

    scheduler = MarketSyncScheduler(
        scheduler=FakeBackgroundScheduler(),
        session_factory=session_factory,
        service_factory=FakeSyncService,
    )

    scheduler.run_scheduled_sync()

    assert calls == [sessions[0], "scheduled"]
    assert sessions[0].closed is True


def test_app_lifecycle_initializes_database_before_starting_and_stops_without_waiting(monkeypatch):
    """Starting before schema initialization or waiting during shutdown makes application lifecycle unreliable."""
    from app import main

    calls = []

    monkeypatch.delenv("SELLHELP_DISABLE_MARKET_SYNC_SCHEDULER", raising=False)
    monkeypatch.setattr(main, "init_db", lambda: calls.append("init_db"))
    monkeypatch.setattr(main.market_sync_scheduler, "start", lambda: calls.append("start"))
    monkeypatch.setattr(main.market_sync_scheduler, "shutdown", lambda: calls.append("shutdown"))

    main.initialize_database()
    main.shutdown_market_sync_scheduler()

    assert calls == ["init_db", "start", "shutdown"]
