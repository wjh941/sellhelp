"""
盈泰副食贸易管理系统 - Pydantic Schemas
用于API请求/响应的数据验证
"""
from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import datetime, date
from decimal import Decimal
from typing import Annotated, Any, List, Literal, Optional


PositiveQuantity = Annotated[float, Field(gt=Decimal("0"))]
PositiveAmount = Annotated[float, Field(gt=Decimal("0"))]
NonNegativeAmount = Annotated[float, Field(ge=Decimal("0"))]
PaymentType = Literal["\u73b0\u7ed3", "\u8d4a\u8d26", "\u90e8\u5206\u7ed3\u8d26"]
ReturnType = Literal["\u5ba2\u6237\u9000\u8d27", "\u4f9b\u5e94\u5546\u9000\u8d27"]


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
    quantity: PositiveQuantity
    unit_price: PositiveAmount
    remark: Optional[str] = None

    @model_validator(mode="after")
    def validate_batch_dates(self):
        if self.production_date and self.expiry_date and self.expiry_date < self.production_date:
            raise ValueError("expiry_date must not be before production_date")
        return self

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
    items: Annotated[List[PurchaseItemCreate], Field(min_length=1)]


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
    quantity: PositiveQuantity
    unit_price: NonNegativeAmount
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
    payment_type: PaymentType = "现结"
    paid_amount: Optional[NonNegativeAmount] = None
    items: Annotated[List[SalesItemCreate], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_payment(self):
        if self.payment_type not in PaymentType.__args__:
            raise ValueError("unsupported payment_type")
        if self.paid_amount is not None and self.paid_amount < 0:
            raise ValueError("paid_amount must not be negative")
        return self


class SalesOrderPay(BaseModel):
    payment_type: PaymentType = "现结"
    paid_amount: Optional[NonNegativeAmount] = None

    @model_validator(mode="after")
    def validate_payment(self):
        if self.payment_type not in PaymentType.__args__:
            raise ValueError("unsupported payment_type")
        if self.paid_amount is not None and self.paid_amount < 0:
            raise ValueError("paid_amount must not be negative")
        return self


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
    return_type: ReturnType
    related_order_no: Optional[str] = None
    partner_id: Optional[int] = None
    product_id: int
    batch_id: Optional[int] = None
    quantity: PositiveQuantity
    refund_amount: NonNegativeAmount = 0
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
    actual_quantity: Annotated[float, Field(ge=0)]
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


# ========== 外部行情待确认账本 ==========
class ExternalMarketQuoteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    product_name: Optional[str] = None
    scope_label: str
    region: str
    quote_kind: str
    source_name: str
    source_url: str
    source_excerpt: str
    observed_at: Optional[date] = None
    fetched_at: datetime
    price: Optional[float] = None
    unit: Optional[str] = None
    trend: Optional[str] = None
    status: str
    dismissed_remark: Optional[str] = None


class ExternalMarketQuoteAcceptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: Optional[int] = Field(None, gt=0)
    price: Optional[float] = None
    unit: Optional[str] = None
    trend: Optional[str] = None
    remark: Optional[str] = None
    operator: Optional[str] = None


class ExternalMarketQuoteDismissCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    remark: Optional[str] = None
    operator: Optional[str] = None


class ExternalMarketSyncRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    trigger: str
    region: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    quotes_created: int
    duplicates_skipped: int
    failure_detail: Optional[str] = None


class ExternalMarketSyncStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_configured: bool
    sync_time: str
    default_region: str
    last_run: Optional[ExternalMarketSyncRunResponse] = None


class ExternalMarketSyncScheduleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sync_time: str = Field(..., pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")


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


# ========== Authentication and audit ==========
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=256)


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    display_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=256)
    role_codes: List[str] = Field(..., min_length=1)


class InitialOwnerRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    display_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=256)


class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=8, max_length=256)
    role_codes: Optional[List[str]] = Field(None, min_length=1)
    is_active: Optional[bool] = None


class AuthUserResponse(BaseModel):
    id: Optional[int]
    username: str
    display_name: str
    role_codes: List[str]
    standalone_mode: bool


class LoginResponse(AuthUserResponse):
    access_token: Optional[str] = None
    token_type: str = "bearer"


class RoleResponse(BaseModel):
    code: str
    name: str
    description: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    timestamp: datetime
    client_ip: Optional[str] = None
    operation_type: str
    operation_detail: str
    status_code: int


class AuditLogPageResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
