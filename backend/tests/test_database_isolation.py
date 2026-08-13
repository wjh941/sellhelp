from app.database import SQLALCHEMY_DATABASE_URL
from app.database import get_db
from app.main import app


def test_pytest_harness_uses_an_in_memory_database():
    assert SQLALCHEMY_DATABASE_URL == "sqlite://"


def test_client_reuses_db_session_override(client, db_session):
    override = app.dependency_overrides[get_db]
    override_generator = override()
    try:
        assert next(override_generator) is db_session
    finally:
        override_generator.close()
