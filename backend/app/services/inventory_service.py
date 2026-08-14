"""
FIFO先进先出库存服务
核心业务逻辑：实现副食批次管理和先进先出出库
确保商品按照最早入库/最早到期的批次优先出库，防止过期亏损
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import math

from ..models.all_models import (
    Product, ProductBatch, PurchaseOrderItem, SalesOrderItem, BatchOutbound,
    InventoryMovement
)


class InventoryService:
    """库存服务 - 核心FIFO逻辑"""

    def __init__(self, db: Session):
        self.db = db

    def get_product_total_stock(self, product_id: int) -> float:
        """获取商品总库存"""
        result = self.db.query(
            func.coalesce(func.sum(ProductBatch.remaining_quantity), 0)
        ).filter(
            ProductBatch.product_id == product_id,
            ProductBatch.remaining_quantity > 0
        ).scalar()
        return float(result or 0)

    def get_product_batches(self, product_id: int) -> List[ProductBatch]:
        """获取商品所有有效批次（按到期日期排序，先进先出优先）"""
        return self.db.query(ProductBatch).filter(
            ProductBatch.product_id == product_id,
            ProductBatch.remaining_quantity > 0
        ).order_by(
            ProductBatch.expiry_date.asc(),
            ProductBatch.production_date.asc()
        ).all()

    def get_saleable_batches(self, product_id: int) -> List[ProductBatch]:
        """Return physical batches that can be sold today."""
        return self.db.query(ProductBatch).filter(
            ProductBatch.product_id == product_id,
            ProductBatch.remaining_quantity > 0,
            (ProductBatch.expiry_date.is_(None) | (ProductBatch.expiry_date > date.today()))
        ).order_by(
            ProductBatch.expiry_date.asc(),
            ProductBatch.production_date.asc()
        ).all()

    def get_batch_by_id(self, batch_id: int) -> Optional[ProductBatch]:
        """根据ID获取批次"""
        return self.db.query(ProductBatch).filter(ProductBatch.id == batch_id).first()

    def find_fifo_batches(self, product_id: int, quantity: float) -> List[Tuple[ProductBatch, float]]:
        """
        FIFO分配：根据需求数量，从最早批次开始分配出库量
        返回 [(批次, 出库数量), ...]
        """
        if quantity <= 0:
            raise ValueError("quantity must be greater than zero")

        batches = self.get_saleable_batches(product_id)
        remaining = quantity
        result = []

        for batch in batches:
            if remaining <= 0:
                break
            take = min(batch.remaining_quantity, remaining)
            if take > 0:
                result.append((batch, take))
                remaining -= take

        if remaining > 0.001:
            raise ValueError(f"库存不足，需要 {quantity}，可用 {quantity - remaining}")

        return result

    def allocate_stock_for_sale(self, product_id: int, quantity: float) -> Tuple[float, List[Dict]]:
        """
        为销售单分配库存（FIFO）
        返回：(加权平均成本价, [批次分配详情])
        """
        allocations = self.find_fifo_batches(product_id, quantity)

        total_cost = 0
        details = []
        for batch, take_qty in allocations:
            cost = batch.purchase_price * take_qty
            total_cost += cost
            details.append({
                "batch_id": batch.id,
                "batch_no": batch.batch_no,
                "quantity": take_qty,
                "unit_cost": batch.purchase_price,
                "expiry_date": str(batch.expiry_date) if batch.expiry_date else None
            })

        avg_cost = total_cost / quantity if quantity > 0 else 0
        return avg_cost, details

    def confirm_outbound(self, sales_item_id: int, product_id: int, quantity: float):
        """
        确认出库：扣减批次库存，记录出库追踪
        """
        if self.db.query(BatchOutbound.id).filter_by(sales_item_id=sales_item_id).first():
            return
        allocations = self.find_fifo_batches(product_id, quantity)
        sales_item = self.db.query(SalesOrderItem).filter(SalesOrderItem.id == sales_item_id).first()
        reference_no = sales_item.sales_order.order_no if sales_item and sales_item.sales_order else None
        sales_order_id = sales_item.sales_order_id if sales_item else None

        for batch, take_qty in allocations:
            # 扣减批次库存
            batch.remaining_quantity -= take_qty

            # 记录出库追踪
            outbound = BatchOutbound(
                sales_item_id=sales_item_id,
                batch_id=batch.id,
                outbound_quantity=take_qty,
                unit_cost=batch.purchase_price
            )
            self.db.add(outbound)
            self.record_movement(
                product_id=product_id,
                batch_id=batch.id,
                direction="outbound",
                quantity=take_qty,
                reason="sale",
                reference_no=reference_no,
                sales_order_id=sales_order_id,
                operator=sales_item.sales_order.operator if sales_item and sales_item.sales_order else None,
            )

        # 检查批次是否过期
        self._check_expiry()

    def reverse_outbound(self, sales_item_id: int):
        """
        冲销出库（退货时使用）
        """
        records = self.db.query(BatchOutbound).filter(
            BatchOutbound.sales_item_id == sales_item_id
        ).all()

        for record in records:
            batch = self.get_batch_by_id(record.batch_id)
            if batch:
                batch.remaining_quantity += record.outbound_quantity
                sales_item = record.sales_item
                sales_order = sales_item.sales_order if sales_item else None
                self.record_movement(
                    product_id=batch.product_id,
                    batch_id=batch.id,
                    direction="inbound",
                    quantity=record.outbound_quantity,
                    reason="sale_reversal",
                    reference_no=sales_order.order_no if sales_order else None,
                    sales_order_id=sales_order.id if sales_order else None,
                    operator=sales_order.operator if sales_order else None,
                )
            self.db.delete(record)

    def record_movement(self, product_id: int, batch_id: Optional[int], direction: str,
                        quantity: float, reason: str, reference_no: Optional[str] = None,
                        purchase_order_id: Optional[int] = None, sales_order_id: Optional[int] = None,
                        return_order_id: Optional[int] = None, stock_take_id: Optional[int] = None,
                        operator: Optional[str] = None, remark: Optional[str] = None) -> InventoryMovement:
        if quantity <= 0:
            raise ValueError("quantity must be greater than zero")
        if direction not in {"inbound", "outbound"}:
            raise ValueError("direction must be inbound or outbound")
        movement = InventoryMovement(
            product_id=product_id,
            batch_id=batch_id,
            direction=direction,
            quantity=quantity,
            reason=reason,
            reference_no=reference_no,
            purchase_order_id=purchase_order_id,
            sales_order_id=sales_order_id,
            return_order_id=return_order_id,
            stock_take_id=stock_take_id,
            operator=operator,
            remark=remark,
        )
        self.db.add(movement)
        return movement

    def add_batch_stock(self, product_id: int, batch_no: str, quantity: float,
                        purchase_price: float, production_date: date = None,
                        expiry_date: date = None) -> ProductBatch:
        """
        增加批次库存（入库时调用）
        """
        if quantity <= 0:
            raise ValueError("quantity must be greater than zero")
        batch = ProductBatch(
            product_id=product_id,
            batch_no=batch_no,
            production_date=production_date,
            expiry_date=expiry_date,
            purchase_price=purchase_price,
            total_quantity=quantity,
            remaining_quantity=quantity
        )
        self.db.add(batch)
        self.db.flush()
        self._check_expiry()
        return batch

    def return_to_batch(self, batch_id: int, quantity: float):
        """
        退回批次库存（退货时使用）
        """
        if quantity <= 0:
            raise ValueError("quantity must be greater than zero")
        batch = self.get_batch_by_id(batch_id)
        if not batch:
            raise ValueError("批次不存在")
        batch.remaining_quantity += quantity

    def _check_expiry(self):
        """检查并标记过期批次"""
        today = date.today()
        self.db.query(ProductBatch).filter(
            ProductBatch.expiry_date <= today,
            ProductBatch.is_expired == False
        ).update({"is_expired": True})

    def get_stock_info(self, product_id: int) -> Dict:
        """获取商品完整库存信息"""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {}

        batches = self.get_product_batches(product_id)
        total_stock = sum(b.remaining_quantity for b in batches)
        stock_value = sum(b.remaining_quantity * b.purchase_price for b in batches)

        today = date.today()
        near_expiry = [b for b in batches
                       if b.expiry_date and (b.expiry_date - today).days <= 30
                       and (b.expiry_date - today).days >= 0]
        expired = [b for b in batches
                   if b.expiry_date and b.expiry_date < today]

        return {
            "product_id": product_id,
            "product_name": product.name,
            "total_stock": total_stock,
            "stock_value": round(stock_value, 2),
            "batches": [{
                "batch_id": b.id,
                "batch_no": b.batch_no,
                "remaining": b.remaining_quantity,
                "purchase_price": b.purchase_price,
                "expiry_date": str(b.expiry_date) if b.expiry_date else None,
                "days_to_expiry": (b.expiry_date - today).days if b.expiry_date else None
            } for b in batches],
            "near_expiry_count": len(near_expiry),
            "expired_count": len(expired)
        }

    def get_all_products_stock(self, include_empty: bool = False) -> List[Dict]:
        """获取所有商品库存"""
        query = self.db.query(Product)
        if not include_empty:
            query = query.filter(Product.is_active == True)
        products = query.all()

        result = []
        for p in products:
            info = self.get_stock_info(p.id)
            if include_empty or info.get("total_stock", 0) > 0:
                result.append(info)
        return result

    def get_expiry_warnings(self, warning_days: int = 30) -> List[Dict]:
        """
        获取临期预警列表
        warning_days: 预警天数，默认30天
        """
        today = date.today()
        cutoff_date = today + timedelta(days=warning_days)

        batches = self.db.query(ProductBatch).filter(
            ProductBatch.remaining_quantity > 0,
            ProductBatch.expiry_date.isnot(None),
            ProductBatch.expiry_date <= cutoff_date
        ).order_by(ProductBatch.expiry_date.asc()).all()

        warnings = []
        for b in batches:
            if b.expiry_date:
                days_left = (b.expiry_date - today).days
                if days_left < 0:
                    level = "expired"
                elif days_left <= 15:
                    level = "critical"
                else:
                    level = "warning"

                product = self.db.query(Product).filter(Product.id == b.product_id).first()
                warnings.append({
                    "product_id": b.product_id,
                    "product_name": product.name if product else "未知",
                    "batch_id": b.id,
                    "batch_no": b.batch_no,
                    "remaining_quantity": b.remaining_quantity,
                    "expiry_date": str(b.expiry_date),
                    "days_to_expiry": days_left,
                    "warning_level": level
                })

        return sorted(warnings, key=lambda x: x["days_to_expiry"])

    def get_stock_value_summary(self) -> Dict:
        """库存价值汇总"""
        products = self.db.query(Product).filter(Product.is_active == True).all()
        total_value = 0
        category_values = {}

        for p in products:
            stock_value = 0
            batches = self.db.query(ProductBatch).filter(
                ProductBatch.product_id == p.id,
                ProductBatch.remaining_quantity > 0
            ).all()
            for b in batches:
                stock_value += b.remaining_quantity * b.purchase_price
            total_value += stock_value

            category = p.category.name if p.category else "未分类"
            if category not in category_values:
                category_values[category] = 0
            category_values[category] += stock_value

        return {
            "total_stock_value": round(total_value, 2),
            "by_category": {k: round(v, 2) for k, v in category_values.items()}
        }
