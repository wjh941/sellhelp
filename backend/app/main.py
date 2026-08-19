"""
盈泰副食贸易管理系统 - FastAPI主入口
"""
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db
from app.desktop_runtime import desktop_data_dir, desktop_static_dir, is_desktop_mode
from app.desktop_startup import prepare_desktop_startup
from app.security import PermissionMiddleware
from app.services.market_sync_scheduler import market_sync_scheduler
from app.services.desktop_backup_scheduler import desktop_backup_scheduler

# 导入所有路由
from app.routers.product_router import router as product_router
from app.routers.supplier_router import router as supplier_router
from app.routers.customer_router import router as customer_router
from app.routers.purchase_router import router as purchase_router
from app.routers.sales_router import router as sales_router
from app.routers.inventory_router import router as inventory_router
from app.routers.return_router import router as return_router
from app.routers.market_router import router as market_router
from app.routers.external_market_router import router as external_market_router
from app.routers.report_router import router as report_router
from app.routers.export_router import router as export_router
from app.routers.finance_router import router as finance_router
from app.routers.system_router import router as system_router
from app.routers.auth_router import audit_router, router as auth_router

@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    try:
        yield
    finally:
        shutdown_runtime_services()


def initialize_database():
    if is_desktop_mode():
        prepare_desktop_startup(desktop_data_dir())
    init_db()
    if is_desktop_mode():
        desktop_backup_scheduler.start()
    if os.getenv("SELLHELP_DISABLE_MARKET_SYNC_SCHEDULER") != "1":
        market_sync_scheduler.start()


def shutdown_market_sync_scheduler():
    market_sync_scheduler.shutdown()


def shutdown_runtime_services():
    if is_desktop_mode():
        desktop_backup_scheduler.shutdown()
    shutdown_market_sync_scheduler()


class SpaStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            return await super().get_response("index.html", scope)


def create_app(static_dir: Path | None = None) -> FastAPI:
    desktop_mode = is_desktop_mode()
    resolved_static_dir = static_dir if static_dir is not None else desktop_static_dir()
    app = FastAPI(
        title="盈泰副食贸易管理系统",
        description="专为东莞高埗新联综合市场盈泰副食贸易部定制的完整商业经营管理系统",
        version="1.0.0",
        docs_url=None if desktop_mode else "/docs",
        redoc_url=None if desktop_mode else "/redoc",
        lifespan=lifespan,
    )
    allowed_origins = [origin.strip() for origin in os.getenv(
        "SELLHELP_ALLOWED_ORIGINS", "http://localhost:8080"
    ).split(",") if origin.strip()]

    # CORS配置 - 允许前端访问
    app.add_middleware(PermissionMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(product_router)
    app.include_router(supplier_router)
    app.include_router(customer_router)
    app.include_router(purchase_router)
    app.include_router(sales_router)
    app.include_router(inventory_router)
    app.include_router(return_router)
    app.include_router(market_router)
    app.include_router(external_market_router)
    app.include_router(report_router)
    app.include_router(export_router)
    app.include_router(finance_router)
    app.include_router(system_router)
    app.include_router(auth_router)
    app.include_router(audit_router)

    @app.get("/api/health")
    def health_check():
        """健康检查"""
        return {
            "status": "ok",
            "system": "盈泰副食贸易管理系统",
            "version": "1.0.0",
            "database": "SQLite",
            "note": "本地单机版，数据存储在 yingtai.db"
        }

    if resolved_static_dir is None:
        @app.get("/")
        def root():
            """根路径"""
            return {
                "name": "盈泰副食贸易管理系统",
                "description": "记账 + 控库存 + 会定价 + 懂行情 + 每周自动分析生意 + 商业经营思维教学",
                "modules": [
                    "基础档案管理",
                    "批次入库系统",
                    "销售开单+FIFO出库",
                    "退货盘点管控",
                    "市场行情记录",
                    "AI智能定价",
                    "每周经营分析报告",
                    "AI生意顾问"
                ],
                "docs": "/docs",
                "status": "运行中"
            }

    if resolved_static_dir is not None:
        app.mount("/", SpaStaticFiles(directory=resolved_static_dir), name="static")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
