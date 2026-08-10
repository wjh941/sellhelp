"""
盈泰副食贸易管理系统 - Pydantic Schemas
用于API请求/响应的数据验证
"""
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List, Any


# ========== 商品分类 ==========
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, comment="分类名称")
    sort_order: int = 0

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 商品 ==========
class ProductBase(BaseModel):
    name: str
    category_id: Optional[int] = None
    spec: Optional[str] = None
    unit: str = "件"
    retail_price: float = 0
    wholesale_price: float = 0
    vip_price: float = 0
    purchase_price: float = 0
    safe_stock: int = 0
    stock_alert_days: int = 30
    is_active: bool = True
    remark: Optional[str] = None

class ProductCreate(ProductBase):
    code: Optional[str] = None

class ProductUpdate(ProductBase):
    code: Optional[str] = None

class ProductResponse(ProductBase):
    id: int
    code: Optional[str] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    category_name: Optional[str] = None
    current_stock: float = 0
    near_expiry_stock: float = 0

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    total: int
    items: List[ProductResponse]


# ========== 供应商 ==========
class SupplierBase(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    payment_term: Optional[str] = None
    cooperation_status: str = "正常合作"
    remark: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(SupplierBase):
    pass

class SupplierResponse(SupplierBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 客户 ==========
class CustomerBase(BaseModel):
    name: str
    customer_type: str = "散户"
    is_vip: bool = False
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    credit_limit: float = 0
    remark: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: int
    current_debt: float = 0
    total_consumption: float = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 入库单 ==========
class PurchaseItemCreate(BaseModel):
    product_id: int
    batch_no: str
    production_date: Optional[date] = None
    expiry_date: Optional[date] = None
    quantity: float
    unit_price: float
    remark: Optional[str] = None

class PurchaseItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    batch_no: str
    production_date: Optional[date] = None
    expiry_date: Optional[date] = None
    quantity: float
    unit_price: float
    amount: float
    remaining_quantity: float = 0

    class Config:
        from_attributes = True


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    purchase_date: Optional[datetime] = None
    operator: Optional[str] = None
    remark: Optional[str] = None
    items: List[PurchaseItemCreate]


class PurchaseOrderResponse(BaseModel):
    id: int
    order_no: str
    supplier_id: int
    supplier_name: Optional[str] = None
    purchase_date: Optional[datetime] = None
    total_amount: float
    operator: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    items: List[PurchaseItemResponse] = []

    class Config:
        from_attributes = True


# ========== 销售单 ==========
class SalesItemCreate(BaseModel):
    product_id: int
    quantity: float
    unit_price: float
    remark: Optional[str] = None

class SalesItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    quantity: float
    unit_price: float
    cost_price: float
    amount: float
    profit: float
    batches_used: Optional[List[dict]] = None

    class Config:
        from_attributes = True


class SalesOrderCreate(BaseModel):
    customer_id: int
    sale_date: Optional[datetime] = None
    operator: Optional[str] = None
    remark: Optional[str] = None
    payment_type: str = "现结"
    paid_amount: Optional[float] = None
    items: List[SalesItemCreate]


class SalesOrderPay(BaseModel):
    payment_type: str = "现结"
    paid_amount: Optional[float] = None


class SalesOrderResponse(BaseModel):
    id: int
    order_no: str
    customer_id: int
    customer_name: Optional[str] = None
    sale_date: Optional[datetime] = None
    total_amount: float
    discount_amount: float
    final_amount: float
    payment_type: str
    paid_amount: float
    debt_amount: float
    customer_type_snapshot: Optional[str] = None
    price_level_used: Optional[str] = None
    operator: Optional[str] = None
    remark: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    items: List[SalesItemResponse] = []

    class Config:
        from_attributes = True


# ========== 退货 ==========
class ReturnOrderCreate(BaseModel):
    return_type: str
    related_order_no: Optional[str] = None
    partner_id: Optional[int] = None
    product_id: int
    batch_id: Optional[int] = None
    quantity: float
    refund_amount: float = 0
    reason: Optional[str] = None
    operator: Optional[str] = None

class ReturnOrderResponse(BaseModel):
    id: int
    order_no: str
    return_type: str
    related_order_no: Optional[str] = None
    partner_id: Optional[int] = None
    product_id: int
    product_name: Optional[str] = None
    batch_id: Optional[int] = None
    batch_no: Optional[str] = None
    quantity: float
    refund_amount: float
    reason: Optional[str] = None
    operator: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 盘点 ==========
class StockTakeItemCreate(BaseModel):
    product_id: int
    batch_id: Optional[int] = None
    actual_quantity: float
    reason: Optional[str] = None

class StockTakeBatchResponse(BaseModel):
    batch_id: int
    batch_no: str
    product_id: int
    product_name: str
    system_quantity: float
    actual_quantity: float
    diff_quantity: float

    class Config:
        from_attributes = True


class StockTakeResponse(BaseModel):
    id: int
    take_date: date
    product_id: int
    product_name: Optional[str] = None
    batch_id: Optional[int] = None
    batch_no: Optional[str] = None
    system_quantity: float
    actual_quantity: float
    diff_quantity: float
    diff_amount: float
    reason: Optional[str] = None
    operator: Optional[str] = None
    confirmed: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 行情 ==========
class MarketPriceCreate(BaseModel):
    record_date: date
    product_id: Optional[int] = None
    price_type: str
    competitor_price: Optional[float] = None
    manufacturer_price: Optional[float] = None
    market_trend: Optional[str] = None
    content: Optional[str] = None
    remark: Optional[str] = None
    operator: Optional[str] = None

class MarketPriceResponse(BaseModel):
    id: int
    record_date: date
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    price_type: str
    competitor_price: Optional[float] = None
    manufacturer_price: Optional[float] = None
    market_trend: Optional[str] = None
    content: Optional[str] = None
    remark: Optional[str] = None
    operator: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== AI定价 ==========
class PricingRequest(BaseModel):
    product_id: int

class PricingReferenceResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    reference_date: Optional[datetime] = None
    cost_floor: float
    normal_price: float
    vip_price: float
    ai_analysis: Optional[str] = None
    factors: Optional[str] = None
    confirmed: bool = False
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 周报 ==========
class WeeklyReportResponse(BaseModel):
    id: int
    week_start: date
    week_end: date
    total_sales: float
    total_profit: float
    order_count: int
    hot_products: Optional[str] = None
    slow_products: Optional[str] = None
    profitable_products: Optional[str] = None
    low_profit_products: Optional[str] = None
    stock_value: float
    overstock_risk: Optional[str] = None
    expired_warning: Optional[str] = None
    customer_debts: Optional[str] = None
    top_customers: Optional[str] = None
    suggestions: Optional[str] = None
    ai_business_advice: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== AI顾问 ==========
class AIQuestionRequest(BaseModel):
    question: str
    context: Optional[str] = None
    session_id: Optional[str] = None

class AIAnswerResponse(BaseModel):
    answer: str
    session_id: str
    data_used: Optional[dict] = None


# ========== 库存查询 ==========
class StockInfo(BaseModel):
    product_id: int
    product_name: str
    total_stock: float
    batches: List[dict]
    stock_value: float
    near_expiry_count: int = 0
    expired_count: int = 0


class ExpiryWarning(BaseModel):
    product_id: int
    product_name: str
    batch_id: int
    batch_no: str
    remaining_quantity: float
    days_to_expiry: int
    expiry_date: date
    warning_level: str


# ========== 通用响应 ==========
class MessageResponse(BaseModel):
    message: str
    data: Optional[Any] = None
