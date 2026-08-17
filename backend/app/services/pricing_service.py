"""
AI定价与分析服务
根据：历史进价、近期行情、竞品价格、商品周转速度、淡旺季
输出三档参考价：保本底价、常规批发价、大客户优惠价
注意：AI只做分析建议，不自动改价
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import json

from ..models.all_models import (
    Product, ProductBatch, SalesOrderItem, MarketPrice, PricingReference,
    WeeklyReport, Category
)
from .inventory_service import InventoryService


class PricingService:
    """AI定价服务"""

    def __init__(self, db: Session):
        self.db = db
        self.inventory = InventoryService(db)

    def calculate_pricing(self, product_id: int) -> Dict:
        """
        计算商品三档参考价
        综合考虑：进价、行情、周转、淡旺季
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"error": "商品不存在"}

        # 1. 获取成本数据
        cost_data = self._get_cost_data(product)

        # 2. 获取行情数据
        market_data = self._get_market_data(product_id)

        # 3. 获取周转数据
        turnover_data = self._get_turnover_data(product_id)

        # 4. 判断淡旺季
        season_factor = self._get_season_factor(product)

        # 5. 计算参考价格
        cost_floor = self._calc_cost_floor(cost_data)
        normal_price = self._calc_normal_price(cost_floor, market_data, turnover_data, season_factor)
        vip_price = self._calc_vip_price(normal_price, turnover_data)

        # 6. 生成AI分析
        analysis = self._generate_analysis(product, cost_data, market_data, turnover_data, season_factor,
                                           cost_floor, normal_price, vip_price)

        # 7. 保存定价参考
        reference = PricingReference(
            product_id=product_id,
            reference_date=datetime.now(),
            cost_floor=round(cost_floor, 2),
            normal_price=round(normal_price, 2),
            vip_price=round(vip_price, 2),
            ai_analysis=analysis,
            factors=json.dumps({
                "cost": cost_data,
                "market": market_data,
                "turnover": turnover_data,
                "season": season_factor
            }, ensure_ascii=False)
        )
        self.db.add(reference)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {
            "product_id": product_id,
            "product_name": product.name,
            "cost_data": cost_data,
            "market_data": market_data,
            "turnover_data": turnover_data,
            "season_factor": season_factor,
            "cost_floor": round(cost_floor, 2),
            "normal_price": round(normal_price, 2),
            "vip_price": round(vip_price, 2),
            "ai_analysis": analysis,
            "current_retail": product.retail_price,
            "current_wholesale": product.wholesale_price,
            "current_vip": product.vip_price
        }

    def _get_cost_data(self, product: Product) -> Dict:
        """获取成本数据"""
        batches = self.db.query(ProductBatch).filter(
            ProductBatch.product_id == product.id,
            ProductBatch.remaining_quantity > 0
        ).all()

        if not batches:
            return {
                "avg_cost": product.purchase_price or 0,
                "latest_cost": product.purchase_price or 0,
                "cost_trend": "无库存"
            }

        total_value = sum(b.remaining_quantity * b.purchase_price for b in batches)
        total_qty = sum(b.remaining_quantity for b in batches)
        avg_cost = total_value / total_qty if total_qty > 0 else 0

        # 最近进价趋势
        latest_batch = sorted(batches, key=lambda x: x.created_at, reverse=True)[0]
        earliest_batch = sorted(batches, key=lambda x: x.created_at)[0]

        if latest_batch.purchase_price > earliest_batch.purchase_price * 1.05:
            trend = "上涨"
        elif latest_batch.purchase_price < earliest_batch.purchase_price * 0.95:
            trend = "下跌"
        else:
            trend = "稳定"

        return {
            "avg_cost": round(avg_cost, 2),
            "latest_cost": latest_batch.purchase_price,
            "cost_trend": trend,
            "stock_value": round(total_value, 2)
        }

    def _get_market_data(self, product_id: int) -> Dict:
        """获取市场行情数据"""
        thirty_days_ago = date.today() - timedelta(days=30)

        market_records = self.db.query(MarketPrice).filter(
            MarketPrice.record_date >= thirty_days_ago
        ).order_by(MarketPrice.record_date.desc()).limit(20).all()

        related_records = [r for r in market_records
                           if r.product_id == product_id or r.product_id is None]

        competitor_prices = [r.competitor_price for r in related_records
                             if r.competitor_price and r.competitor_price > 0]

        avg_competitor = sum(competitor_prices) / len(competitor_prices) if competitor_prices else 0

        # 市场趋势
        trends = [r.market_trend for r in related_records if r.market_trend]
        up_count = trends.count("上涨")
        down_count = trends.count("下跌")

        if up_count > down_count * 1.5:
            market_trend = "上涨"
        elif down_count > up_count * 1.5:
            market_trend = "下跌"
        else:
            market_trend = "持平"

        return {
            "competitor_avg": round(avg_competitor, 2),
            "market_trend": market_trend,
            "recent_records_count": len(related_records)
        }

    def _get_turnover_data(self, product_id: int) -> Dict:
        """获取商品周转数据"""
        # 最近30天销售数据
        thirty_days_ago = datetime.now() - timedelta(days=30)

        sales_items = self.db.query(SalesOrderItem).filter(
            SalesOrderItem.product_id == product_id
        ).all()

        # 计算总销量和总利润
        total_qty = sum(si.quantity for si in sales_items)
        total_profit = sum(si.profit for si in sales_items)

        # 当前库存
        current_stock = self.inventory.get_product_total_stock(product_id)

        # 周转天数估算
        daily_sales = total_qty / 30 if total_qty > 0 else 0
        turnover_days = current_stock / daily_sales if daily_sales > 0 else 999

        # 判断周转状态
        if turnover_days <= 15:
            turnover_status = "快速周转"
        elif turnover_days <= 30:
            turnover_status = "正常周转"
        elif turnover_days <= 60:
            turnover_status = "偏慢"
        else:
            turnover_status = "滞销"

        # 利润率
        sales_amount = sum(si.amount for si in sales_items)
        profit_margin = (total_profit / sales_amount * 100) if sales_amount > 0 else 0

        return {
            "sales_30d_qty": round(total_qty, 2),
            "sales_30d_profit": round(total_profit, 2),
            "current_stock": round(current_stock, 2),
            "turnover_days": round(turnover_days, 1),
            "turnover_status": turnover_status,
            "profit_margin": round(profit_margin, 2)
        }

    def _get_season_factor(self, product: Product) -> str:
        """判断淡旺季"""
        month = date.today().month
        category_name = product.category.name if product.category else ""

        # 节日品/礼盒：节前旺季
        if "节日" in category_name or "礼盒" in category_name:
            if month in [1, 2, 9, 10]:
                return "旺季"
            elif month in [6, 7, 8]:
                return "淡季"
            else:
                return "平季"

        # 饮料：夏季旺季
        if "饮料" in category_name:
            if month in [5, 6, 7, 8]:
                return "旺季"
            elif month in [12, 1, 2]:
                return "淡季"
            else:
                return "平季"

        # 粮油调味：相对稳定
        return "平季"

    def _calc_cost_floor(self, cost_data: Dict) -> float:
        """计算保本底价"""
        avg_cost = cost_data.get("avg_cost", 0)
        # 考虑5%的损耗和资金成本
        return avg_cost * 1.05

    def _calc_normal_price(self, cost_floor: float, market_data: Dict,
                           turnover_data: Dict, season_factor: str) -> float:
        """计算常规批发价"""
        if cost_floor <= 0:
            return 0

        # 基础加价率
        markup_rate = 0.15  # 15%基础毛利

        # 根据周转调整
        turnover_status = turnover_data.get("turnover_status", "正常周转")
        if turnover_status == "快速周转":
            markup_rate = 0.12  # 快周转可以低毛利
        elif turnover_status == "偏慢":
            markup_rate = 0.20  # 慢周转需要高毛利
        elif turnover_status == "滞销":
            markup_rate = 0.25  # 滞销品需要更高毛利

        # 根据市场行情调整
        market_trend = market_data.get("market_trend", "持平")
        competitor_avg = market_data.get("competitor_avg", 0)

        if market_trend == "上涨":
            markup_rate += 0.03
        elif market_trend == "下跌":
            markup_rate -= 0.02

        # 参考竞品价格
        if competitor_avg > 0:
            suggested = competitor_avg * 0.98  # 比竞品略低
            markup_rate = max(markup_rate, (suggested / cost_floor) - 1)

        # 淡旺季调整
        if season_factor == "旺季":
            markup_rate += 0.03
        elif season_factor == "淡季":
            markup_rate -= 0.02

        return cost_floor * (1 + markup_rate)

    def _calc_vip_price(self, normal_price: float, turnover_data: Dict) -> float:
        """计算大客户优惠价"""
        if normal_price <= 0:
            return 0

        # 大客户通常有5-10%折扣
        turnover_status = turnover_data.get("turnover_status", "正常周转")

        if turnover_status == "快速周转":
            vip_discount = 0.95  # 5%折扣
        else:
            vip_discount = 0.92  # 8%折扣

        return normal_price * vip_discount

    def _generate_analysis(self, product: Product, cost_data: Dict, market_data: Dict,
                           turnover_data: Dict, season_factor: str,
                           cost_floor: float, normal_price: float, vip_price: float) -> str:
        """生成AI定价分析说明"""
        analysis_parts = []

        analysis_parts.append(f"【商品】{product.name}")

        # 成本分析
        if cost_data["cost_trend"] == "上涨":
            analysis_parts.append("📈 成本呈上涨趋势，建议适当提高售价")
        elif cost_data["cost_trend"] == "下跌":
            analysis_parts.append("📉 成本呈下跌趋势，可考虑调低售价或保持利润")

        # 周转分析
        turnover_status = turnover_data.get("turnover_status", "")
        if turnover_status == "快速周转":
            analysis_parts.append(f"⚡ 周转快速（{turnover_data['turnover_days']:.0f}天），可薄利多销")
        elif turnover_status == "滞销":
            analysis_parts.append(f"⚠️ 周转缓慢（{turnover_data['turnover_days']:.0f}天），建议降价清库存或优化定价")

        # 行情分析
        if market_data["market_trend"] == "上涨":
            analysis_parts.append("📊 市场行情上涨，有提价空间")
        elif market_data["market_trend"] == "下跌":
            analysis_parts.append("📊 市场行情下跌，需注意不要定太高价")

        # 淡旺季
        if season_factor == "旺季":
            analysis_parts.append("🔥 当前处于旺季，可适当提高毛利")
        elif season_factor == "淡季":
            analysis_parts.append("❄️ 当前处于淡季，建议降低毛利走量")

        analysis_parts.append(f"\n💡 参考定价建议：")
        analysis_parts.append(f"  保本底价：¥{cost_floor:.2f}（不亏钱的底线）")
        analysis_parts.append(f"  常规批发：¥{normal_price:.2f}（普通客户价格）")
        analysis_parts.append(f"  大客户价：¥{vip_price:.2f}（晨升膳食等VIP价）")

        return "\n".join(analysis_parts)

    def confirm_pricing(self, reference_id: int, operator: str) -> bool:
        """人工确认定价"""
        ref = self.db.query(PricingReference).filter(PricingReference.id == reference_id).first()
        if not ref:
            return False

        ref.confirmed = True
        ref.confirmed_by = operator
        ref.confirmed_at = datetime.now()
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return True
