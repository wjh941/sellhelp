"""
每周经营分析报告服务
自动生成周报，包含：热销/滞销、利润分析、库存风险、客户分析、AI建议
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import json

from ..models.all_models import (
    Product, ProductBatch, SalesOrder, SalesOrderItem,
    Customer, MarketPrice, WeeklyReport, Category, ReturnOrder
)
from .inventory_service import InventoryService
from .pricing_service import PricingService


class ReportService:
    """周报生成服务"""

    def __init__(self, db: Session):
        self.db = db
        self.inventory = InventoryService(db)

    def generate_weekly_report(self, end_date: date = None) -> WeeklyReport:
        """
        生成周度经营分析报告
        默认以当前日期为结束日期，往前推7天
        """
        if end_date is None:
            end_date = date.today()
        start_date = end_date - timedelta(days=6)

        # 1. 基础销售数据
        sales_data = self._get_sales_summary(start_date, end_date)

        # 2. 热销商品TOP10
        hot_products = self._get_hot_products(start_date, end_date)

        # 3. 滞销商品（30天无销量但有库存）
        slow_products = self._get_slow_products()

        # 4. 利润分析
        profit_analysis = self._analyze_profit_structure(start_date, end_date)

        # 5. 库存风险分析
        stock_risk = self._analyze_stock_risk()

        # 6. 临期预警
        expiry_warning = self.inventory.get_expiry_warnings(warning_days=30)

        # 7. 客户分析
        customer_analysis = self._analyze_customers(start_date, end_date)

        # 8. AI建议
        suggestions = self._generate_suggestions(
            hot_products, slow_products, profit_analysis, stock_risk, customer_analysis
        )

        # 9. 商业思维周报内容
        business_advice = self._generate_business_advice(
            sales_data, profit_analysis, stock_risk, customer_analysis
        )

        # 创建报告
        report = WeeklyReport(
            week_start=start_date,
            week_end=end_date,
            total_sales=sales_data["total_sales"],
            total_profit=sales_data["total_profit"],
            order_count=sales_data["order_count"],
            hot_products=json.dumps(hot_products, ensure_ascii=False),
            slow_products=json.dumps(slow_products, ensure_ascii=False),
            profitable_products=json.dumps(profit_analysis["top_profit"], ensure_ascii=False),
            low_profit_products=json.dumps(profit_analysis["low_profit"], ensure_ascii=False),
            stock_value=stock_risk["total_value"],
            overstock_risk=json.dumps(stock_risk["overstock_items"], ensure_ascii=False),
            expired_warning=json.dumps(expiry_warning, ensure_ascii=False),
            customer_debts=json.dumps(customer_analysis["debt_analysis"], ensure_ascii=False),
            top_customers=json.dumps(customer_analysis["top_customers"], ensure_ascii=False),
            suggestions=suggestions,
            ai_business_advice=business_advice,
            created_at=datetime.now()
        )

        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def _get_sales_summary(self, start_date: date, end_date: date) -> Dict:
        """销售汇总"""
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        orders = self.db.query(SalesOrder).filter(
            and_(
                SalesOrder.sale_date >= start_dt,
                SalesOrder.sale_date <= end_dt,
                SalesOrder.status == "已完成"
            )
        ).all()

        total_sales = sum(o.final_amount for o in orders)
        order_count = len(orders)

        # 计算总利润
        total_profit = 0
        for order in orders:
            for item in order.items:
                total_profit += item.profit

        return {
            "total_sales": round(total_sales, 2),
            "total_profit": round(total_profit, 2),
            "order_count": order_count,
            "avg_order_value": round(total_sales / order_count, 2) if order_count > 0 else 0
        }

    def _get_hot_products(self, start_date: date, end_date: date) -> List[Dict]:
        """热销商品TOP10"""
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        results = self.db.query(
            SalesOrderItem.product_id,
            Product.name,
            func.sum(SalesOrderItem.quantity).label("total_qty"),
            func.sum(SalesOrderItem.amount).label("total_amount"),
            func.sum(SalesOrderItem.profit).label("total_profit")
        ).join(
            SalesOrder, SalesOrderItem.sales_order_id == SalesOrder.id
        ).join(
            Product, SalesOrderItem.product_id == Product.id
        ).filter(
            and_(
                SalesOrder.sale_date >= start_dt,
                SalesOrder.sale_date <= end_dt,
                SalesOrder.status == "已完成"
            )
        ).group_by(
            SalesOrderItem.product_id
        ).order_by(
            desc("total_amount")
        ).limit(10).all()

        return [{
            "product_id": r[0],
            "product_name": r[1],
            "total_qty": round(r[2], 2),
            "total_amount": round(r[3], 2),
            "total_profit": round(r[4], 2)
        } for r in results]

    def _get_slow_products(self) -> List[Dict]:
        """滞销商品 - 30天无销量但有库存"""
        thirty_days_ago = datetime.now() - timedelta(days=30)

        # 找出有库存但30天无销售的商品
        products = self.db.query(Product).filter(Product.is_active == True).all()
        slow_items = []

        for product in products:
            stock = self.inventory.get_product_total_stock(product.id)
            if stock <= 0:
                continue

            # 检查最近30天是否有销售
            recent_sales = self.db.query(SalesOrderItem).join(SalesOrder).filter(
                SalesOrderItem.product_id == product.id,
                SalesOrder.sale_date >= thirty_days_ago,
                SalesOrder.status == "已完成"
            ).count()

            if recent_sales == 0:
                stock_value = 0
                batches = self.db.query(ProductBatch).filter(
                    ProductBatch.product_id == product.id,
                    ProductBatch.remaining_quantity > 0
                ).all()
                for b in batches:
                    stock_value += b.remaining_quantity * b.purchase_price

                slow_items.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "current_stock": round(stock, 2),
                    "stock_value": round(stock_value, 2),
                    "days_no_sales": 30
                })

        return sorted(slow_items, key=lambda x: x["stock_value"], reverse=True)[:20]

    def _analyze_profit_structure(self, start_date: date, end_date: date) -> Dict:
        """利润结构分析"""
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # 按分类统计利润
        category_profits = self.db.query(
            Category.name,
            func.sum(SalesOrderItem.amount).label("total_amount"),
            func.sum(SalesOrderItem.profit).label("total_profit"),
            func.sum(SalesOrderItem.quantity).label("total_qty")
        ).join(
            Product, SalesOrderItem.product_id == Product.id
        ).join(
            Category, Product.category_id == Category.id, isouter=True
        ).join(
            SalesOrder, SalesOrderItem.sales_order_id == SalesOrder.id
        ).filter(
            and_(
                SalesOrder.sale_date >= start_dt,
                SalesOrder.sale_date <= end_dt,
                SalesOrder.status == "已完成"
            )
        ).group_by(Category.id).all()

        # 高利润商品TOP10
        top_profit = self.db.query(
            SalesOrderItem.product_id,
            Product.name,
            func.sum(SalesOrderItem.profit).label("total_profit"),
            func.sum(SalesOrderItem.amount).label("total_amount")
        ).join(
            Product, SalesOrderItem.product_id == Product.id
        ).join(
            SalesOrder, SalesOrderItem.sales_order_id == SalesOrder.id
        ).filter(
            and_(
                SalesOrder.sale_date >= start_dt,
                SalesOrder.sale_date <= end_dt,
                SalesOrder.status == "已完成"
            )
        ).group_by(SalesOrderItem.product_id).order_by(desc("total_profit")).limit(10).all()

        # 低利润/走量商品
        low_profit = []
        for item in top_profit:
            profit = item[2] or 0
            amount = item[3] or 0
            margin = (profit / amount * 100) if amount > 0 else 0
            if margin < 5 and amount > 0:  # 利润率低于5%
                low_profit.append({
                    "product_id": item[0],
                    "product_name": item[1],
                    "total_profit": round(profit, 2),
                    "total_amount": round(amount, 2),
                    "profit_margin": round(margin, 2)
                })

        return {
            "by_category": [{
                "category": cp[0] or "未分类",
                "total_amount": round(cp[1], 2),
                "total_profit": round(cp[2], 2),
                "profit_margin": round(cp[2] / cp[1] * 100, 2) if cp[1] > 0 else 0
            } for cp in category_profits],
            "top_profit": [{
                "product_id": p[0],
                "product_name": p[1],
                "total_profit": round(p[2], 2),
                "total_amount": round(p[3], 2),
                "profit_margin": round(p[2] / p[3] * 100, 2) if p[3] > 0 else 0
            } for p in top_profit],
            "low_profit": low_profit
        }

    def _analyze_stock_risk(self) -> Dict:
        """库存风险分析"""
        stock_summary = self.inventory.get_stock_value_summary()
        expiry_warnings = self.inventory.get_expiry_warnings(warning_days=30)

        # 积压商品（库存价值超过平均水平3倍）
        all_stock = self.inventory.get_all_products_stock(include_empty=False)
        if all_stock:
            avg_value = sum(s["stock_value"] for s in all_stock) / len(all_stock)
        else:
            avg_value = 0

        overstock = [s for s in all_stock if s["stock_value"] > avg_value * 3]
        overstock = sorted(overstock, key=lambda x: x["stock_value"], reverse=True)[:10]

        return {
            "total_value": stock_summary["total_stock_value"],
            "by_category": stock_summary["by_category"],
            "overstock_items": overstock,
            "expiry_count": len(expiry_warnings),
            "critical_expiry_count": len([w for w in expiry_warnings if w["warning_level"] == "critical"])
        }

    def _analyze_customers(self, start_date: date, end_date: date) -> Dict:
        """客户分析"""
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # 客户消费排行
        customer_sales = self.db.query(
            Customer.id,
            Customer.name,
            Customer.customer_type,
            Customer.is_vip,
            func.sum(SalesOrder.final_amount).label("total_amount"),
            func.count(SalesOrder.id).label("order_count")
        ).join(
            SalesOrder, Customer.id == SalesOrder.customer_id
        ).filter(
            and_(
                SalesOrder.sale_date >= start_dt,
                SalesOrder.sale_date <= end_dt,
                SalesOrder.status == "已完成"
            )
        ).group_by(Customer.id).order_by(desc("total_amount")).limit(10).all()

        # 欠款客户分析
        debt_customers = self.db.query(
            Customer.id,
            Customer.name,
            Customer.customer_type,
            Customer.current_debt,
            Customer.credit_limit
        ).filter(
            Customer.current_debt > 0
        ).order_by(desc(Customer.current_debt)).all()

        return {
            "top_customers": [{
                "customer_id": c[0],
                "name": c[1],
                "type": c[2],
                "is_vip": c[3],
                "total_amount": round(c[4], 2),
                "order_count": c[5]
            } for c in customer_sales],
            "debt_analysis": [{
                "customer_id": c[0],
                "name": c[1],
                "type": c[2],
                "current_debt": round(c[3], 2),
                "credit_limit": round(c[4], 2)
            } for c in debt_customers]
        }

    def _generate_suggestions(self, hot_products, slow_products,
                               profit_analysis, stock_risk,
                               customer_analysis) -> str:
        """生成下周建议"""
        suggestions = []

        # 备货建议
        if hot_products:
            top_item = hot_products[0]
            suggestions.append(f"📦 备货建议：{top_item['product_name']}销量最高，建议保持充足库存")

        if slow_products:
            names = [s["product_name"] for s in slow_products[:3]]
            suggestions.append(f"⚠️ 清库建议：{', '.join(names)} 滞销超过30天，考虑特价清仓或捆绑销售")

        # 库存风险
        if stock_risk["overstock_items"]:
            top_overstock = stock_risk["overstock_items"][0]
            suggestions.append(f"💰 减仓建议：{top_overstock['product_name']} 库存价值过高，注意资金占用")

        # 临期预警
        if stock_risk["expiry_count"] > 0:
            suggestions.append(f"⏰ 临期处理：有 {stock_risk['expiry_count']} 个批次接近保质期，需优先销售")

        # 定价建议
        low_profit = profit_analysis.get("low_profit", [])
        if low_profit:
            names = [p["product_name"] for p in low_profit[:3]]
            suggestions.append(f"💲 调价建议：{', '.join(names)} 利润过低，可考虑提价或替换")

        return "\n".join(suggestions)

    def _generate_business_advice(self, sales_data: Dict, profit_analysis: Dict,
                                   stock_risk: Dict, customer_analysis: Dict) -> str:
        """生成商业思维周报"""
        advice_parts = []

        advice_parts.append("=" * 50)
        advice_parts.append("📊 盈泰副食 · 每周商业思维周报")
        advice_parts.append("=" * 50)

        # 本周表现
        advice_parts.append(f"\n【本周业绩】")
        advice_parts.append(f"  销售额：¥{sales_data['total_sales']:,.2f}")
        advice_parts.append(f"  利润：¥{sales_data['total_profit']:,.2f}")
        profit_rate = (sales_data['total_profit'] / sales_data['total_sales'] * 100) if sales_data['total_sales'] > 0 else 0
        advice_parts.append(f"  利润率：{profit_rate:.1f}%")
        advice_parts.append(f"  订单数：{sales_data['order_count']}笔")

        # 利润结构分析
        by_category = profit_analysis.get("by_category", [])
        if by_category:
            advice_parts.append(f"\n【利润结构】")
            advice_parts.append("  各品类利润贡献：")
            for cat in by_category[:5]:
                bar = "█" * int(cat["total_profit"] / max(c["total_profit"] for c in by_category) * 20) if by_category else ""
                advice_parts.append(f"    {cat['category']}: ¥{cat['total_profit']:,.2f} ({cat['profit_margin']:.1f}%) {bar}")

        # 关键洞察
        advice_parts.append(f"\n【关键洞察】")

        # 引流品 vs 利润品分析
        if by_category:
            sorted_by_margin = sorted(by_category, key=lambda x: x["profit_margin"])
            if sorted_by_margin:
                low_margin = sorted_by_margin[0]
                high_margin = sorted_by_margin[-1]
                advice_parts.append(f"  💡 {low_margin['category']}利润率仅{low_margin['profit_margin']:.1f}%，属于引流品，用来锁客户")
                advice_parts.append(f"  💡 {high_margin['category']}利润率{high_margin['profit_margin']:.1f}%，是利润核心，重点推广")

        # 库存健康度
        advice_parts.append(f"\n【库存健康度】")
        advice_parts.append(f"  库存总值：¥{stock_risk['total_value']:,.2f}")
        if stock_risk["expiry_count"] > 0:
            advice_parts.append(f"  ⚠️ 临期批次：{stock_risk['expiry_count']}个（30天内过期）")
        if stock_risk["overstock_items"]:
            advice_parts.append(f"  ⚠️ 积压商品：{len(stock_risk['overstock_items'])}个")

        # 客户体系
        debt_count = len(customer_analysis.get("debt_analysis", []))
        advice_parts.append(f"\n【客户体系】")
        advice_parts.append(f"  欠款客户：{debt_count}个")

        # 核心建议
        advice_parts.append(f"\n【本周行动清单】")
        advice_parts.append(f"  1. 检查临期商品，制定特价清仓方案")
        advice_parts.append(f"  2. 分析低利润商品，评估是否提价或替换")
        advice_parts.append(f"  3. 跟进欠款客户回款")
        advice_parts.append(f"  4. 优化引流品与利润品的产品组合")

        advice_parts.append(f"\n【商业思维提示】")
        advice_parts.append(f"  - 不要靠低价抢单，靠产品结构和服务锁客户")
        advice_parts.append(f"  - 粮油是引流品，调味礼盒是利润品，组合好才赚钱")
        advice_parts.append(f"  - 快周转比高差价更重要，钱要流动起来")

        return "\n".join(advice_parts)

    def get_latest_report(self) -> Optional[WeeklyReport]:
        """获取最新周报"""
        return self.db.query(WeeklyReport).order_by(WeeklyReport.created_at.desc()).first()

    def get_reports_history(self, limit: int = 10) -> List[WeeklyReport]:
        """获取周报历史"""
        return self.db.query(WeeklyReport).order_by(WeeklyReport.created_at.desc()).limit(limit).all()
