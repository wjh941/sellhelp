"""
盈泰副食贸易管理系统 - FastAPI主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import sys

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db

# 导入所有路由
from app.routers.product_router import router as product_router
from app.routers.supplier_router import router as supplier_router
from app.routers.customer_router import router as customer_router
from app.routers.purchase_router import router as purchase_router
from app.routers.sales_router import router as sales_router
from app.routers.inventory_router import router as inventory_router
from app.routers.return_router import router as return_router
from app.routers.market_router import router as market_router
from app.routers.report_router import router as report_router
from app.routers.export_router import router as export_router
from app.routers.finance_router import router as finance_router
from app.routers.system_router import router as system_router

app = FastAPI(
    title="盈泰副食贸易管理系统",
    description="专为东莞高埗新联综合市场盈泰副食贸易部定制的完整商业经营管理系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.on_event("startup")
def initialize_database():
    init_db()

# CORS配置 - 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
app.include_router(report_router)
app.include_router(export_router)
app.include_router(finance_router)
app.include_router(system_router)


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
