"""
盈泰副食贸易管理系统 - 数据库配置
本地单机版 SQLite 数据库
"""
import os
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from app.desktop_runtime import desktop_data_dir, is_desktop_mode

def sqlite_database_path() -> Path:
    if is_desktop_mode():
        return desktop_data_dir() / "data" / "sellhelp.db"
    return Path(__file__).resolve().parent.parent / "yingtai.db"


DB_PATH = str(sqlite_database_path())
SQLALCHEMY_DATABASE_URL = os.getenv("SELLHELP_DATABASE_URL", f"sqlite:///{sqlite_database_path().as_posix()}")


def get_active_sqlite_db_path() -> str:
    """Return the configured SQLite file path for file-copy operations."""
    url = make_url(SQLALCHEMY_DATABASE_URL)
    database = url.database
    if (
        url.get_backend_name() != "sqlite"
        or not database
        or database == ":memory:"
        or database.startswith("file:")
        or url.query.get("mode") == "memory"
    ):
        raise ValueError("Backup and restore require a file-based SQLite database")
    return os.path.abspath(database)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
MIGRATION_MANAGED_TABLES = {"roles", "users", "user_roles", "audit_logs"}


def get_db():
    """获取数据库会话（FastAPI依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表"""
    # Keep the legacy Phase 1 bootstrap while reserving identity/audit DDL for Alembic.
    legacy_tables = [
        table for table in Base.metadata.sorted_tables
        if table.name not in MIGRATION_MANAGED_TABLES
    ]
    Base.metadata.create_all(bind=engine, tables=legacy_tables)
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as connection:
        inspector = inspect(connection)
        if inspector.has_table("external_market_quotes") and "dismissed_remark" not in {
            column["name"] for column in inspector.get_columns("external_market_quotes")
        }:
            connection.exec_driver_sql("ALTER TABLE external_market_quotes ADD COLUMN dismissed_remark TEXT")
