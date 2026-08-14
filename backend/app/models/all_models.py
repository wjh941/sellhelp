"""
盈泰副食贸易管理系统 - 完整数据库模型
涵盖9大模块：基础档案、批次入库、销售出库、退货盘点、行情、AI定价、周报、商学院
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime, date as date_type
import sys
import os

# 将项目根目录加入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base

# ========== 模块1：基础档案管理 ==========

class Category(Base):
    """商品分类表"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, comment="分类名称：粮油/调味/饮料/零食/礼盒/节日品")
    sort_order = Column(Integer, default=0, comment="排序")
    created_at = Column(DateTime, default=datetime.now)

    products = relationship("Product", back_populates="category")


class Product(Base):
    """商品表 - 三档价格体系"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, comment="商品编码")
    name = Column(String(200), nullable=False, comment="商品名称")
    category_id = Column(Integer, ForeignKey("categories.id"), comment="分类ID")
    spec = Column(String(100), comment="规格")
    unit = Column(String(20), nullable=False, default="件", comment="单位")
    image_url = Column(String(500), comment="商品图片")

    # 三档价格体系
    retail_price = Column(Float, default=0, comment="零售价")
    wholesale_price = Column(Float, default=0, comment="普通批发价")
    vip_price = Column(Float, default=0, comment="大客户价（晨升膳食专属）")

    # 进价记录
    purchase_price = Column(Float, default=0, comment="当前参考进价")

    # 库存控制
    safe_stock = Column(Integer, default=0, comment="安全库存")
    stock_alert_days = Column(Integer, default=30, comment="临期预警天数")

    # 商品状态
    is_active = Column(Boolean, default=True, comment="是否在售")
    remark = Column(Text, comment="备注")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    category = relationship("Category", back_populates="products")
    batches = relationship("ProductBatch", back_populates="product")
    inventory_movements = relationship("InventoryMovement", back_populates="product")


class Supplier(Base):
    """供应商档案"""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="供应商/厂家名称")
    contact_person = Column(String(50), comment="联系人")
    phone = Column(String(30), comment="电话")
    address = Column(String(500), comment="地址")
    payment_term = Column(String(100), comment="账期说明")
    cooperation_status = Column(String(50), default="正常合作", comment="合作状态")
    remark = Column(Text, comment="备注")
    created_at = Column(DateTime, default=datetime.now)

    purchase_records = relationship("PurchaseOrder", back_populates="supplier")


class Customer(Base):
    """客户档案 - 含欠款额度、累计消费"""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="客户名称")
    customer_type = Column(String(50), default="散户", comment="客户类型：散户/小店/工厂/食堂/VIP")
    is_vip = Column(Boolean, default=False, comment="是否核心大客户（晨升膳食）")
    contact_person = Column(String(50), comment="联系人")
    phone = Column(String(30), comment="电话")
    address = Column(String(500), comment="地址")

    # 财务数据
    credit_limit = Column(Float, default=0, comment="欠款额度")
    current_debt = Column(Float, default=0, comment="当前欠款")
    total_consumption = Column(Float, default=0, comment="累计消费金额")
    remark = Column(Text, comment="备注")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    sales_orders = relationship("SalesOrder", back_populates="customer")
    receivable_ledgers = relationship("ReceivableLedger", back_populates="customer")


# ========== 模块2：批次入库系统 ==========

class PurchaseOrder(Base):
    """入库单主表"""
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(50), unique=True, index=True, nullable=False, comment="入库单号")
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    purchase_date = Column(DateTime, nullable=False, comment="采购日期")
    total_amount = Column(Float, default=0, comment="入库总金额")
    operator = Column(String(50), comment="操作员")
    remark = Column(Text, comment="备注")
    created_at = Column(DateTime, default=datetime.now)

    supplier = relationship("Supplier", back_populates="purchase_records")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    """入库单明细 - 每一条明细对应一个批次"""
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    # 批次信息（副食核心）
    batch_no = Column(String(100), nullable=False, comment="批次号")
    production_date = Column(Date, comment="生产日期")
    expiry_date = Column(Date, comment="到期时间")

    # 采购数据
    quantity = Column(Float, nullable=False, comment="入库数量")
    unit_price = Column(Float, nullable=False, comment="采购单价")
    amount = Column(Float, nullable=False, comment="金额")

    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    batch = relationship("ProductBatch", back_populates="purchase_item", uselist=False)


class ProductBatch(Base):
    """商品批次表 - FIFO先进先出的核心"""
    __tablename__ = "product_batches"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    purchase_item_id = Column(Integer, ForeignKey("purchase_order_items.id"), unique=True)
    batch_no = Column(String(100), nullable=False, comment="批次号")
    production_date = Column(Date, comment="生产日期")
    expiry_date = Column(Date, comment="到期时间")
    purchase_price = Column(Float, nullable=False, comment="采购单价")

    # 库存追踪
    total_quantity = Column(Float, nullable=False, comment="入库总量")
    remaining_quantity = Column(Float, nullable=False, comment="剩余数量（FIFO出库追踪）")

    # 状态
    is_expired = Column(Boolean, default=False, comment="是否已过期")
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    product = relationship("Product", back_populates="batches")
    purchase_item = relationship("PurchaseOrderItem", back_populates="batch")
    outbound_records = relationship("BatchOutbound", back_populates="batch")
    inventory_movements = relationship("InventoryMovement", back_populates="batch")

    __table_args__ = (
        Index("ix_batches_product_expiry", "product_id", "expiry_date"),
    )


# ========== 模块3：销售开单 + 出库系统（FIFO） ==========

class SalesOrder(Base):
    """销售单主表"""
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(50), unique=True, index=True, nullable=False, comment="销售单号")
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    sale_date = Column(DateTime, nullable=False, comment="销售日期")

    # 金额信息
    total_amount = Column(Float, default=0, comment="销售总额")
    discount_amount = Column(Float, default=0, comment="优惠金额")
    final_amount = Column(Float, default=0, comment="实收金额")

    # 结算方式
    payment_type = Column(String(20), default="现结", comment="结算方式：现结/赊账/部分结账")
    paid_amount = Column(Float, default=0, comment="已付金额")
    debt_amount = Column(Float, default=0, comment="欠款金额")

    # 客户信息快照
    customer_type_snapshot = Column(String(50), comment="下单时客户类型")
    price_level_used = Column(String(20), comment="使用的价格档次")

    operator = Column(String(50), comment="操作员")
    remark = Column(Text)
    status = Column(String(20), default="已完成", comment="状态：已完成/已退货")
    created_at = Column(DateTime, default=datetime.now)

    customer = relationship("Customer", back_populates="sales_orders")
    items = relationship("SalesOrderItem", back_populates="sales_order", cascade="all, delete-orphan")
    receivable_ledgers = relationship("ReceivableLedger", back_populates="sales_order")


class ReceivableLedger(Base):
    __tablename__ = "receivable_ledgers"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="SET NULL"), index=True)
    amount = Column(Float, nullable=False, comment="Signed receivable balance movement")
    reason = Column(String(50), nullable=False)
    reference_no = Column(String(50), index=True)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    customer = relationship("Customer", back_populates="receivable_ledgers")
    sales_order = relationship("SalesOrder", back_populates="receivable_ledgers")


class SalesOrderItem(Base):
    """销售单明细"""
    __tablename__ = "sales_order_items"

    id = Column(Integer, primary_key=True, index=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    # 销售信息
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False, comment="销售单价")
    cost_price = Column(Float, default=0, comment="成本价（来自批次）")
    amount = Column(Float, nullable=False, comment="小计金额")
    profit = Column(Float, default=0, comment="利润")

    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    sales_order = relationship("SalesOrder", back_populates="items")
    outbound_records = relationship("BatchOutbound", back_populates="sales_item")


class BatchOutbound(Base):
    """批次出库记录 - 精确追踪每次FIFO出库使用的批次"""
    __tablename__ = "batch_outbound"

    id = Column(Integer, primary_key=True, index=True)
    sales_item_id = Column(Integer, ForeignKey("sales_order_items.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("product_batches.id"), nullable=False)
    outbound_quantity = Column(Float, nullable=False, comment="从该批次出库数量")
    unit_cost = Column(Float, nullable=False, comment="该批次单位成本")
    created_at = Column(DateTime, default=datetime.now)

    sales_item = relationship("SalesOrderItem", back_populates="outbound_records")
    batch = relationship("ProductBatch", back_populates="outbound_records")


class InventoryMovement(Base):
    """Immutable physical inventory ledger entry."""
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("product_batches.id", ondelete="SET NULL"), index=True)
    direction = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    reason = Column(String(50), nullable=False, index=True)
    reference_no = Column(String(100), index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="SET NULL"), index=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="SET NULL"), index=True)
    return_order_id = Column(Integer, ForeignKey("return_orders.id", ondelete="SET NULL"), index=True)
    stock_take_id = Column(Integer, ForeignKey("stock_takes.id", ondelete="SET NULL"), index=True)
    operator = Column(String(50))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    product = relationship("Product", back_populates="inventory_movements")
    batch = relationship("ProductBatch", back_populates="inventory_movements")


# ========== 模块4：退货、盘点 ==========

class ReturnOrder(Base):
    """退货单 - 客户退货 + 供应商退货"""
    __tablename__ = "return_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(50), unique=True, index=True, nullable=False, comment="退货单号")
    return_type = Column(String(20), nullable=False, comment="退货类型：客户退货/供应商退货")
    related_order_no = Column(String(50), comment="关联的原单号")
    partner_id = Column(Integer, comment="客户ID或供应商ID")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("product_batches.id"), comment="批次ID")
    quantity = Column(Float, nullable=False)
    refund_amount = Column(Float, default=0, comment="退款金额")
    reason = Column(String(500), comment="退货原因")
    operator = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)


class StockTake(Base):
    """库存盘点记录"""
    __tablename__ = "stock_takes"

    id = Column(Integer, primary_key=True, index=True)
    take_date = Column(Date, nullable=False, comment="盘点日期")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("product_batches.id"))
    system_quantity = Column(Float, nullable=False, comment="系统数量")
    actual_quantity = Column(Float, nullable=False, comment="实际盘点数量")
    diff_quantity = Column(Float, nullable=False, comment="盘盈盘亏数量（正盈/负亏）")
    diff_amount = Column(Float, default=0, comment="盘盈盘亏金额")
    reason = Column(String(500), comment="差异原因")
    operator = Column(String(50))
    confirmed = Column(Boolean, default=False, comment="是否已确认")
    created_at = Column(DateTime, default=datetime.now)


# ========== 模块5：市场行情记录 ==========

class MarketPrice(Base):
    """市场行情记录"""
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, index=True)
    record_date = Column(Date, nullable=False, comment="记录日期")
    product_id = Column(Integer, ForeignKey("products.id"), comment="关联商品（可选）")

    # 行情类型
    price_type = Column(String(50), nullable=False, comment="行情类型：同行报价/厂家调价/市场涨跌/节日行情/淡季行情")

    # 价格信息
    competitor_price = Column(Float, comment="同行报价")
    manufacturer_price = Column(Float, comment="厂家报价")
    market_trend = Column(String(20), comment="市场趋势：上涨/持平/下跌")

    # 详细说明
    content = Column(Text, comment="行情详细记录")
    remark = Column(Text)
    operator = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)


# ========== 外部行情待确认账本 ==========

class ExternalMarketQuote(Base):
    __tablename__ = "external_market_quotes"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    scope_label = Column(String(100), nullable=False)
    region = Column(String(50), nullable=False)
    quote_kind = Column(String(20), nullable=False)
    source_name = Column(String(200), nullable=False)
    source_url = Column(String(1000), nullable=False)
    source_excerpt = Column(Text, nullable=False)
    observed_at = Column(Date, nullable=True)
    fetched_at = Column(DateTime, default=datetime.now, nullable=False)
    price = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    trend = Column(String(20), nullable=True)
    status = Column(String(20), default="pending", nullable=False, index=True)
    quote_key = Column(String(64), unique=True, nullable=False, index=True)
    accepted_market_price_id = Column(Integer, ForeignKey("market_prices.id"), nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)


class ExternalMarketSyncRun(Base):
    __tablename__ = "external_market_sync_runs"

    id = Column(Integer, primary_key=True, index=True)
    trigger = Column(String(20), nullable=False)
    region = Column(String(50), nullable=False)
    started_at = Column(DateTime, default=datetime.now, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, index=True)
    quotes_created = Column(Integer, default=0, nullable=False)
    duplicates_skipped = Column(Integer, default=0, nullable=False)
    failure_detail = Column(Text, nullable=True)


class ExternalMarketSyncLock(Base):
    __tablename__ = "external_market_sync_locks"

    name = Column(String(50), primary_key=True)
    acquired_at = Column(DateTime, default=datetime.now, nullable=False)


# ========== 模块6：AI定价参考 ==========

class PricingReference(Base):
    """AI定价参考记录（仅供参考，不自动改价）"""
    __tablename__ = "pricing_references"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    reference_date = Column(DateTime, nullable=False)

    # AI输出三档参考价
    cost_floor = Column(Float, default=0, comment="保本底价")
    normal_price = Column(Float, default=0, comment="常规批发价")
    vip_price = Column(Float, default=0, comment="大客户优惠价")

    # AI分析依据
    ai_analysis = Column(Text, comment="AI分析说明")
    factors = Column(Text, comment="影响因素JSON：进价/行情/竞品/周转/淡旺季")

    # 人工确认
    confirmed = Column(Boolean, default=False, comment="是否人工确认")
    confirmed_by = Column(String(50))
    confirmed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)


# ========== 模块7：每周经营分析报告 ==========

class WeeklyReport(Base):
    """每周经营分析报告"""
    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True, index=True)
    week_start = Column(Date, nullable=False, comment="周开始日期")
    week_end = Column(Date, nullable=False, comment="周结束日期")

    # 销售数据
    total_sales = Column(Float, default=0, comment="本周销售额")
    total_profit = Column(Float, default=0, comment="本周利润")
    order_count = Column(Integer, default=0, comment="订单数")

    # 商品分析（JSON存储）
    hot_products = Column(Text, comment="热销商品JSON")
    slow_products = Column(Text, comment="滞销商品JSON")
    profitable_products = Column(Text, comment="高利润商品JSON")
    low_profit_products = Column(Text, comment="低利润/走量商品JSON")

    # 库存分析
    stock_value = Column(Float, default=0, comment="库存总价值")
    overstock_risk = Column(Text, comment="库存积压风险JSON")
    expired_warning = Column(Text, comment="临期预警JSON")

    # 客户分析
    customer_debts = Column(Text, comment="客户欠款分析JSON")
    top_customers = Column(Text, comment="优质客户JSON")

    # AI建议
    suggestions = Column(Text, comment="下周备货建议、避坑建议、调价建议")
    ai_business_advice = Column(Text, comment="商业思维周报内容")

    created_at = Column(DateTime, default=datetime.now)


# ========== 模块8：AI生意顾问对话历史 ==========

class AIChatHistory(Base):
    """AI生意顾问对话历史"""
    __tablename__ = "ai_chat_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), index=True, comment="会话ID")
    role = Column(String(20), nullable=False, comment="角色：user/assistant")
    content = Column(Text, nullable=False, comment="对话内容")
    business_context = Column(Text, comment="上下文信息JSON")
    created_at = Column(DateTime, default=datetime.now)


# ========== 模块9：系统配置 ==========

class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, comment="配置值")
    description = Column(String(500))
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
