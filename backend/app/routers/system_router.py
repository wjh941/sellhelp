"""
系统管理 API路由 - 数据库备份、滞销商品、系统配置
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, date, timedelta
import os
import shutil
import json
import re

from ..database import get_active_sqlite_db_path, get_db, DB_PATH
from ..models.all_models import Product, ProductBatch, SalesOrder, SalesOrderItem, SystemConfig, WeeklyReport

router = APIRouter(prefix="/api/system", tags=["系统管理"])

_BACKUP_FILENAME = re.compile(r"(?:yingtai_backup|pre_restore)_\d{8}_\d{6}\.db")


def _backup_directory() -> str:
    return os.path.join(os.path.dirname(DB_PATH), "backup")


def _resolve_backup_file(filename: str) -> str:
    if os.path.basename(filename) != filename or not _BACKUP_FILENAME.fullmatch(filename):
        raise HTTPException(status_code=400, detail="Invalid backup filename")
    return os.path.join(_backup_directory(), filename)


def _active_database_path() -> str:
    try:
        return get_active_sqlite_db_path()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ========== 数据库备份 ==========

@router.post("/backup")
def backup_database(
    db: Session = Depends(get_db)
):
    """备份数据库"""
    database_path = _active_database_path()
    if not os.path.exists(database_path):
        raise HTTPException(status_code=404, detail="数据库文件不存在")

    backup_dir = _backup_directory()
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"yingtai_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    shutil.copy2(database_path, backup_path)

    # 更新备份记录
    config = db.query(SystemConfig).filter(SystemConfig.key == "last_backup").first()
    backup_info = json.dumps({
        "filename": backup_filename,
        "path": backup_path,
        "timestamp": datetime.now().isoformat(),
        "size": os.path.getsize(backup_path)
    }, ensure_ascii=False)

    if config:
        config.value = backup_info
    else:
        config = SystemConfig(
            key="last_backup",
            value=backup_info,
            description="最近一次数据库备份信息"
        )
        db.add(config)
    db.commit()

    return {
        "message": "备份成功",
        "backup_file": backup_filename,
        "backup_path": backup_path,
        "file_size": os.path.getsize(backup_path),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/backups")
def list_backups(
):
    """列出所有备份"""
    backup_dir = _backup_directory()

    if not os.path.exists(backup_dir):
        return {"backups": [], "total_size": 0}

    backups = []
    total_size = 0

    for filename in sorted(os.listdir(backup_dir), reverse=True):
        if _BACKUP_FILENAME.fullmatch(filename):
            filepath = _resolve_backup_file(filename)
            if not os.path.isfile(filepath):
                continue
            size = os.path.getsize(filepath)
            total_size += size
            backups.append({
                "filename": filename,
                "size": size,
                "created_at": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
            })

    return {
        "backups": backups,
        "total_count": len(backups),
        "total_size": total_size
    }


@router.post("/restore")
def restore_database(
    backup_file: str = Query(..., description="备份文件名"),
):
    """恢复数据库"""
    database_path = _active_database_path()
    backup_path = _resolve_backup_file(backup_file)
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="备份文件不存在")

    # 恢复前先备份当前数据库
    pre_backup = None
    if os.path.exists(database_path):
        pre_backup = _resolve_backup_file(f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(database_path, pre_backup)

    # 恢复
    shutil.copy2(backup_path, database_path)

    return {
        "message": "数据库恢复成功，请重启系统",
        "backup_file": backup_file,
        "pre_restore_backup": pre_backup
    }


@router.delete("/backups/{filename:path}")
def delete_backup(
    filename: str,
):
    """删除备份"""
    backup_path = _resolve_backup_file(filename)
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="备份文件不存在")

    os.remove(backup_path)
    return {"message": "删除成功"}


@router.get("/backups/{filename:path}")
def download_backup(
    filename: str,
):
    """下载备份文件"""
    backup_path = _resolve_backup_file(filename)
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="备份文件不存在")

    return FileResponse(
        path=backup_path,
        filename=filename,
        media_type="application/octet-stream"
    )


# ========== 滞销商品管理 ==========

@router.get("/slow-products", response_model=List[dict])
def get_slow_products(
    days: int = Query(30, ge=7, le=365, description="滞销判断天数"),
    category_id: Optional[int] = None,
    min_stock_value: float = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """获取滞销商品列表"""
    from ..services.inventory_service import InventoryService
    inventory_service = InventoryService(db)

    days_ago = datetime.now() - timedelta(days=days)

    query = db.query(Product).filter(Product.is_active == True)
    if category_id:
        query = query.filter(Product.category_id == category_id)

    products = query.all()
    slow_items = []

    for product in products:
        stock = inventory_service.get_product_total_stock(product.id)
        if stock <= 0:
            continue

        # 检查近N天是否有销售
        recent_sales = db.query(SalesOrderItem).join(SalesOrder).filter(
            SalesOrderItem.product_id == product.id,
            SalesOrder.sale_date >= days_ago,
            SalesOrder.status == "已完成"
        ).count()

        if recent_sales == 0:
            # 计算库存价值
            stock_value = 0
            batches = db.query(ProductBatch).filter(
                ProductBatch.product_id == product.id,
                ProductBatch.remaining_quantity > 0
            ).all()
            for b in batches:
                stock_value += b.remaining_quantity * b.purchase_price

            if stock_value >= min_stock_value:
                # 计算周转天数（历史销量）
                total_sales_qty = db.query(func.sum(SalesOrderItem.quantity)).join(SalesOrder).filter(
                    SalesOrderItem.product_id == product.id,
                    SalesOrder.status == "已完成"
                ).scalar() or 0

                slow_items.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "category": product.category.name if product.category else None,
                    "current_stock": round(stock, 2),
                    "stock_value": round(stock_value, 2),
                    "days_no_sales": days,
                    "total_sales_qty": round(total_sales_qty, 2)
                })

    return sorted(slow_items, key=lambda x: x["stock_value"], reverse=True)


@router.post("/slow-products/{product_id}/clear-suggestion")
def generate_clear_suggestion(product_id: int, db: Session = Depends(get_db)):
    """生成滞销商品清仓建议"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    from ..services.inventory_service import InventoryService
    inventory_service = InventoryService(db)

    stock = inventory_service.get_product_total_stock(product_id)
    stock_value = inventory_service.get_stock_info(product_id).get("stock_value", 0)

    # 获取历史销售价格
    recent_sales = db.query(SalesOrderItem).join(SalesOrder).filter(
        SalesOrderItem.product_id == product_id,
        SalesOrder.status == "已完成"
    ).order_by(SalesOrder.id.desc()).limit(10).all()

    avg_sale_price = 0
    if recent_sales:
        avg_sale_price = sum(i.unit_price for i in recent_sales) / len(recent_sales)

    # 生成建议
    suggestions = []
    current_price = product.wholesale_price or product.retail_price

    if stock_value > 10000:
        suggestions.append("库存积压严重，建议大幅降价清仓或捆绑销售")
    elif stock_value > 5000:
        suggestions.append("库存较多，建议批发特价或买赠活动")
    else:
        suggestions.append("库存适中，可考虑小幅降价促进销售")

    # 建议价格
    suggested_prices = {
        "clearance_price": round(current_price * 0.7, 2),  # 7折清仓
        "bundle_price": round(current_price * 0.85, 2),  # 85折捆绑
        "break_even_price": round(product.purchase_price * 1.05, 2)  # 保本价
    }

    return {
        "product": product.name,
        "current_stock": stock,
        "stock_value": round(stock_value, 2),
        "current_price": current_price,
        "avg_sale_price": round(avg_sale_price, 2),
        "suggested_prices": suggested_prices,
        "suggestions": suggestions,
        "actions": [
            "设置临期特价区，组合清仓",
            "联系老客户推荐特价商品",
            "考虑拆分散卖或捆绑热销品",
            "如为礼盒类，可保存至明年节前销售"
        ]
    }


# ========== 库存积压统计 ==========

@router.get("/overstock-analysis")
def get_overstock_analysis(
    db: Session = Depends(get_db)
):
    """库存积压分析"""
    from ..services.inventory_service import InventoryService
    inventory_service = InventoryService(db)

    all_stock = inventory_service.get_all_products_stock(include_empty=False)
    total_value = sum(s["stock_value"] for s in all_stock)

    # 分类统计
    by_category = {}
    for s in all_stock:
        cat = s.get("category", "未分类")
        if cat not in by_category:
            by_category[cat] = {"value": 0, "count": 0}
        by_category[cat]["value"] += s["stock_value"]
        by_category[cat]["count"] += 1

    # 找出占比超过10%的积压商品
    overstock = []
    for s in all_stock:
        if total_value > 0 and s["stock_value"] / total_value > 0.1:
            overstock.append({
                "product_name": s["product_name"],
                "stock_value": s["stock_value"],
                "percentage": round(s["stock_value"] / total_value * 100, 1),
                "current_stock": s["total_stock"]
            })

    # 按价值排序的TOP10
    top10 = sorted(all_stock, key=lambda x: x["stock_value"], reverse=True)[:10]

    return {
        "total_stock_value": round(total_value, 2),
        "product_count": len(all_stock),
        "by_category": by_category,
        "overstock_products": overstock,
        "top10_by_value": top10,
        "health_score": _calculate_stock_health(all_stock)
    }


def _calculate_stock_health(stock_list: list) -> dict:
    """计算库存健康度评分"""
    if not stock_list:
        return {"score": 100, "level": "优秀"}

    # 基础分
    score = 100

    # 检查积压
    total_value = sum(s["stock_value"] for s in stock_list)
    if total_value > 0:
        for s in stock_list:
            ratio = s["stock_value"] / total_value
            if ratio > 0.15:  # 单商品占比超过15%
                score -= 10
            elif ratio > 0.1:
                score -= 5

    # 检查品种多样性
    categories = set(s.get("category", "") for s in stock_list)
    if len(categories) < 3:
        score -= 10  # 品类过少
    elif len(categories) >= 5:
        score += 5  # 品类丰富

    score = max(0, min(100, score))

    if score >= 80:
        level = "优秀"
    elif score >= 60:
        level = "良好"
    elif score >= 40:
        level = "一般"
    else:
        level = "较差"

    return {
        "score": score,
        "level": level,
        "suggestion": "库存结构健康，继续保持" if score >= 80 else
                      "部分商品库存占比过高，建议优化" if score >= 60 else
                      "库存结构需要调整，注意分散风险"
    }


# ========== 系统配置 ==========

@router.get("/config")
def get_system_config(db: Session = Depends(get_db)):
    """获取系统配置"""
    configs = db.query(SystemConfig).all()
    result = {}
    for c in configs:
        try:
            result[c.key] = json.loads(c.value) if c.value else None
        except:
            result[c.key] = c.value
    return result


@router.put("/config/{key}")
def update_system_config(
    key: str,
    value: str,
    description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """更新系统配置"""
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if config:
        config.value = value
        if description:
            config.description = description
    else:
        config = SystemConfig(key=key, value=value, description=description)
        db.add(config)

    db.commit()
    return {"message": "配置更新成功"}


@router.get("/info")
def get_system_info(db: Session = Depends(get_db)):
    """获取系统信息"""
    # 统计数据
    product_count = db.query(Product).filter(Product.is_active == True).count()
    customer_count = db.query(Customer).count()
    supplier_count = db.query(Supplier).count()
    sales_count = db.query(SalesOrder).count()
    stock_value = db.query(ProductBatch).filter(ProductBatch.remaining_quantity > 0).count()

    # 数据库大小
    try:
        database_path = get_active_sqlite_db_path()
    except ValueError:
        database_path = None
    db_size = os.path.getsize(database_path) if database_path and os.path.exists(database_path) else 0

    # 最近周报
    latest_report = db.query(WeeklyReport).order_by(WeeklyReport.created_at.desc()).first()

    return {
        "system": "盈泰副食贸易管理系统",
        "version": "2.0.0",
        "database": {
            "path": database_path,
            "size": db_size,
            "tables": {
                "products": product_count,
                "customers": customer_count,
                "suppliers": supplier_count,
                "sales_orders": sales_count,
                "batch_records": stock_value
            }
        },
        "latest_report": str(latest_report.created_at) if latest_report else None,
        "server_time": datetime.now().isoformat()
    }


# 需要的导入
from ..models.all_models import Supplier, Customer
