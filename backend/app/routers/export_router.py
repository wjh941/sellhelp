"""Downloadable exports for sales, inventory, customers, stock takes, and weekly reports."""

from datetime import datetime
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.all_models import Customer, Product, ProductBatch, PurchaseOrder, SalesOrder, StockTake, WeeklyReport
from ..services.document_export_service import download_response
from ..services.inventory_service import InventoryService


router = APIRouter(prefix="/api/export", tags=["导出打印"])


def _binary_response(title: str, sections, file_format: str, filename: str):
    return download_response(title, sections, file_format, filename)


@router.get("/sales/{order_id}")
def export_sales_order(order_id: int, format: str = "json", db: Session = Depends(get_db)):
    """Export a sales document while preserving legacy JSON and print responses."""
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="销售单不存在")
    result = _build_sales_order_data(order, db)
    if format == "json":
        return result
    if format == "print":
        return _generate_delivery_note(order, result)
    return _binary_response("销售单", _sales_sections(result), format, f"sales-order-{order.order_no}")


@router.get("/purchase/{order_id}")
def export_purchase_order(order_id: int, format: str = "json", db: Session = Depends(get_db)):
    """Export a purchase document while preserving legacy JSON and print responses."""
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="入库单不存在")
    result = _build_purchase_order_data(order, db)
    if format == "json":
        return result
    if format == "print":
        return _generate_purchase_print(order, result)
    return _binary_response("入库单", _purchase_sections(result), format, f"purchase-order-{order.order_no}")


@router.get("/customer-statement/{customer_id}")
def export_customer_statement(
    customer_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "json",
    db: Session = Depends(get_db),
):
    result = _customer_statement_data(customer_id, start_date, end_date, db)
    if format == "json":
        return result
    return _binary_response("客户对账单", _customer_statement_sections(result), format, f"customer-statement-{customer_id}")


@router.get("/stock-report")
def export_stock_report(
    category_id: Optional[int] = None,
    include_empty: bool = False,
    format: str = "json",
    db: Session = Depends(get_db),
):
    result = _stock_report_data(category_id, include_empty, db)
    if format == "json":
        return result
    return _binary_response("库存报表", _stock_report_sections(result), format, "inventory-report")


@router.get("/expiry-report")
def export_expiry_report(
    warning_days: int = 30,
    level: Optional[str] = None,
    format: str = "json",
    db: Session = Depends(get_db),
):
    warnings = InventoryService(db).get_expiry_warnings(warning_days)
    if level:
        warnings = [warning for warning in warnings if warning["warning_level"] == level]
    result = {
        "export_time": datetime.now().isoformat(),
        "warning_days": warning_days,
        "total_warnings": len(warnings),
        "critical_count": len([warning for warning in warnings if warning["warning_level"] == "critical"]),
        "items": warnings,
    }
    if format == "json":
        return result
    sections = [
        ("临期预警", [("product_name", "商品"), ("batch_no", "批次"), ("remaining_quantity", "剩余库存"), ("expiry_date", "到期日期"), ("days_to_expiry", "剩余天数"), ("warning_level", "预警级别")], warnings),
    ]
    return _binary_response("临期预警报表", sections, format, "expiry-report")


@router.get("/weekly-reports/{report_id}")
def export_weekly_report(report_id: int, format: str = "xlsx", db: Session = Depends(get_db)):
    report = db.query(WeeklyReport).filter(WeeklyReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="周报不存在")
    return _binary_response("周度经营报表", _weekly_report_sections(report), format, f"weekly-report-{report.week_end}")


@router.get("/stock-takes")
def export_stock_takes(
    take_date: Optional[str] = None,
    product_id: Optional[int] = None,
    confirmed: Optional[bool] = None,
    format: str = "xlsx",
    db: Session = Depends(get_db),
):
    query = db.query(StockTake)
    if take_date:
        query = query.filter(StockTake.take_date == take_date)
    if product_id:
        query = query.filter(StockTake.product_id == product_id)
    if confirmed is not None:
        query = query.filter(StockTake.confirmed == confirmed)
    records = query.order_by(StockTake.id.desc()).all()
    rows = [_stock_take_row(record, db) for record in records]
    sections = [("库存盘点历史", _stock_take_columns(), rows)]
    return _binary_response("库存盘点历史", sections, format, "stock-take-history")


@router.get("/sales-history")
def export_sales_history(
    customer_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "xlsx",
    db: Session = Depends(get_db),
):
    query = db.query(SalesOrder)
    if customer_id:
        query = query.filter(SalesOrder.customer_id == customer_id)
    if start_date:
        query = query.filter(SalesOrder.sale_date >= start_date)
    if end_date:
        query = query.filter(SalesOrder.sale_date <= end_date)
    orders = query.order_by(SalesOrder.sale_date.desc()).all()
    rows = [_sales_history_row(order) for order in orders]
    sections = [("销售历史", _sales_history_columns(), rows)]
    return _binary_response("销售历史", sections, format, "sales-history")


def _customer_statement_data(customer_id: int, start_date: Optional[str], end_date: Optional[str], db: Session) -> dict:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    query = db.query(SalesOrder).filter(SalesOrder.customer_id == customer_id)
    if start_date:
        query = query.filter(SalesOrder.sale_date >= start_date)
    if end_date:
        query = query.filter(SalesOrder.sale_date <= end_date)
    orders = query.order_by(SalesOrder.sale_date.asc()).all()
    return {
        "customer": {"id": customer.id, "name": customer.name, "type": customer.customer_type, "phone": customer.phone, "address": customer.address, "credit_limit": customer.credit_limit, "current_debt": customer.current_debt},
        "period": {"start": start_date or "全部", "end": end_date or "全部"},
        "summary": {"order_count": len(orders), "total_amount": round(sum(order.total_amount for order in orders), 2), "total_paid": round(sum(order.paid_amount for order in orders), 2), "total_debt": round(sum(order.debt_amount for order in orders), 2)},
        "orders": [{"order_no": order.order_no, "date": str(order.sale_date), "total_amount": order.total_amount, "paid_amount": order.paid_amount, "debt_amount": order.debt_amount, "payment_type": order.payment_type, "items_count": len(order.items)} for order in orders],
    }


def _stock_report_data(category_id: Optional[int], include_empty: bool, db: Session) -> dict:
    stock_data = InventoryService(db).get_all_products_stock(include_empty=include_empty)
    if category_id:
        stock_data = [item for item in stock_data if item.get("category_id") == category_id]
    return {"export_time": datetime.now().isoformat(), "total_products": len(stock_data), "stock_value": sum(item["stock_value"] for item in stock_data), "items": stock_data}


def _weekly_report_sections(report: WeeklyReport):
    metrics = [
        {"metric": "报告区间", "value": f"{report.week_start} 至 {report.week_end}"},
        {"metric": "销售额", "value": report.total_sales},
        {"metric": "利润", "value": report.total_profit},
        {"metric": "订单数", "value": report.order_count},
        {"metric": "库存总值", "value": report.stock_value},
        {"metric": "下周经营建议", "value": report.suggestions or ""},
        {"metric": "生意顾问摘要", "value": report.ai_business_advice or ""},
    ]
    sections = [("经营概览", [("metric", "指标"), ("value", "数值")], metrics)]
    for title, source in (("热销商品", report.hot_products), ("高利润商品", report.profitable_products), ("滞销商品", report.slow_products), ("库存积压风险", report.overstock_risk), ("临期预警", report.expired_warning), ("客户欠款", report.customer_debts)):
        rows = _json_rows(source)
        if rows:
            keys = list(dict.fromkeys(key for row in rows for key in row))
            sections.append((title, [(key, key) for key in keys], rows))
    return sections


def _stock_report_sections(result: dict):
    summary = [{"metric": "导出时间", "value": result["export_time"]}, {"metric": "商品数", "value": result["total_products"]}, {"metric": "库存总值", "value": result["stock_value"]}]
    return [("库存概览", [("metric", "指标"), ("value", "数值")], summary), ("库存明细", [("product_name", "商品"), ("total_stock", "库存"), ("stock_value", "库存价值")], result["items"])]


def _customer_statement_sections(result: dict):
    customer = result["customer"]
    summary = [
        {"metric": "客户", "value": customer["name"]}, {"metric": "客户类型", "value": customer["type"]}, {"metric": "联系电话", "value": customer["phone"]},
        {"metric": "账期", "value": f"{result['period']['start']} 至 {result['period']['end']}"}, {"metric": "订单数", "value": result["summary"]["order_count"]},
        {"metric": "销售金额", "value": result["summary"]["total_amount"]}, {"metric": "已收金额", "value": result["summary"]["total_paid"]}, {"metric": "欠款金额", "value": result["summary"]["total_debt"]},
    ]
    columns = [("order_no", "单号"), ("date", "日期"), ("total_amount", "订单金额"), ("paid_amount", "已收"), ("debt_amount", "欠款"), ("payment_type", "结算方式"), ("items_count", "明细数")]
    return [("对账概览", [("metric", "指标"), ("value", "数值")], summary), ("销售明细", columns, result["orders"])]


def _sales_sections(result: dict):
    summary = [{"metric": "单号", "value": result["order_no"]}, {"metric": "客户", "value": result["customer"]["name"]}, {"metric": "日期", "value": result["date"]}, {"metric": "结算方式", "value": result["payment"]["type"]}, {"metric": "订单金额", "value": result["payment"]["total_amount"]}, {"metric": "已收金额", "value": result["payment"]["paid_amount"]}, {"metric": "欠款金额", "value": result["payment"]["debt_amount"]}]
    columns = [("product_name", "商品"), ("spec", "规格"), ("unit", "单位"), ("quantity", "数量"), ("unit_price", "单价"), ("cost_price", "成本"), ("amount", "金额"), ("profit", "利润")]
    return [("销售单信息", [("metric", "指标"), ("value", "数值")], summary), ("销售明细", columns, result["items"])]


def _purchase_sections(result: dict):
    summary = [{"metric": "单号", "value": result["order_no"]}, {"metric": "供应商", "value": result["supplier"]["name"]}, {"metric": "日期", "value": result["date"]}, {"metric": "订单金额", "value": result["total_amount"]}]
    columns = [("product_name", "商品"), ("spec", "规格"), ("unit", "单位"), ("batch_no", "批次"), ("quantity", "数量"), ("unit_price", "单价"), ("amount", "金额")]
    return [("入库单信息", [("metric", "指标"), ("value", "数值")], summary), ("入库明细", columns, result["items"])]


def _stock_take_columns():
    return [("take_date", "盘点日期"), ("product_name", "商品"), ("batch_no", "批次"), ("system_quantity", "系统数量"), ("actual_quantity", "实际数量"), ("diff_quantity", "差异数量"), ("diff_amount", "差异金额"), ("reason", "原因"), ("operator", "操作人"), ("confirmed", "已确认")]


def _stock_take_row(record: StockTake, db: Session) -> dict:
    product = db.get(Product, record.product_id)
    batch = db.get(ProductBatch, record.batch_id) if record.batch_id else None
    return {"take_date": record.take_date, "product_name": product.name if product else "未知商品", "batch_no": batch.batch_no if batch else "", "system_quantity": record.system_quantity, "actual_quantity": record.actual_quantity, "diff_quantity": record.diff_quantity, "diff_amount": record.diff_amount, "reason": record.reason, "operator": record.operator, "confirmed": "是" if record.confirmed else "否"}


def _sales_history_columns():
    return [("order_no", "单号"), ("sale_date", "销售日期"), ("customer", "客户"), ("total_amount", "订单金额"), ("final_amount", "实收金额"), ("paid_amount", "已收"), ("debt_amount", "欠款"), ("payment_type", "结算方式"), ("status", "状态"), ("operator", "操作人")]


def _sales_history_row(order: SalesOrder) -> dict:
    return {"order_no": order.order_no, "sale_date": order.sale_date, "customer": order.customer.name if order.customer else "散客", "total_amount": order.total_amount, "final_amount": order.final_amount, "paid_amount": order.paid_amount, "debt_amount": order.debt_amount, "payment_type": order.payment_type, "status": order.status, "operator": order.operator}


def _json_rows(value: Optional[str]) -> list[dict]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return []
    return [row for row in parsed if isinstance(row, dict)] if isinstance(parsed, list) else []


def _build_sales_order_data(order: SalesOrder, db: Session) -> dict:
    items = []
    for item in order.items:
        product = db.get(Product, item.product_id)
        items.append({"product_name": product.name if product else "未知商品", "spec": product.spec if product else "", "unit": product.unit if product else "", "quantity": item.quantity, "unit_price": item.unit_price, "cost_price": item.cost_price, "amount": item.amount, "profit": item.profit})
    return {"order_no": order.order_no, "customer": {"name": order.customer.name if order.customer else "散客", "type": order.customer_type_snapshot, "price_level": order.price_level_used}, "date": str(order.sale_date), "operator": order.operator, "payment": {"type": order.payment_type, "total_amount": order.total_amount, "paid_amount": order.paid_amount, "debt_amount": order.debt_amount}, "items": items, "remark": order.remark, "status": order.status}


def _build_purchase_order_data(order: PurchaseOrder, db: Session) -> dict:
    items = []
    for item in order.items:
        product = db.get(Product, item.product_id)
        items.append({"product_name": product.name if product else "未知商品", "spec": product.spec if product else "", "unit": product.unit if product else "", "batch_no": item.batch_no, "production_date": str(item.production_date) if item.production_date else None, "expiry_date": str(item.expiry_date) if item.expiry_date else None, "quantity": item.quantity, "unit_price": item.unit_price, "amount": item.amount})
    return {"order_no": order.order_no, "supplier": {"name": order.supplier.name if order.supplier else "", "contact": order.supplier.contact_person if order.supplier else "", "phone": order.supplier.phone if order.supplier else ""}, "date": str(order.purchase_date), "operator": order.operator, "total_amount": order.total_amount, "items": items, "remark": order.remark}


def _generate_delivery_note(order: SalesOrder, data: dict) -> dict:
    return {"print_type": "delivery_note", "title": "盈泰副食贸易部 - 送货单", "order": data, "print_time": datetime.now().isoformat()}


def _generate_purchase_print(order: PurchaseOrder, data: dict) -> dict:
    return {"print_type": "purchase_order", "title": "盈泰副食贸易部 - 入库单", "order": data, "print_time": datetime.now().isoformat()}
