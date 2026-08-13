from app.database import SQLALCHEMY_DATABASE_URL


def test_pytest_harness_uses_an_in_memory_database():
    assert SQLALCHEMY_DATABASE_URL == "sqlite://"
