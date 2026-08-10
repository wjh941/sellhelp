"""
商品与分类 API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.all_models import Product, Category
from ..schemas.all_schemas import (
    CategoryCreate, CategoryUpdate, CategoryResponse,
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse,
    MessageResponse
)
from ..services.inventory_service import InventoryService

router = APIRouter(prefix="/api", tags=["商品管理"])

# ========== 分类管理 ==========

@router.get("/categories", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    """获取所有分类"""
    categories = db.query(Category).order_by(Category.sort_order).all()
    return categories


@router.post("/categories", response_model=CategoryResponse)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    """创建分类"""
    existing = db.query(Category).filter(Category.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="分类名称已存在")
    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, data: CategoryCreate, db: Session = Depends(get_db)):
    """更新分类"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    for key, value in data.model_dump().items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}", response_model=MessageResponse)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """删除分类"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    if category.products:
        raise HTTPException(status_code=400, detail="该分类下还有商品，无法删除")
    db.delete(category)
    db.commit()
    return MessageResponse(message="删除成功")


# ========== 商品管理 ==========

@router.get("/products", response_model=ProductListResponse)
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    keyword: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """分页获取商品列表"""
    query = db.query(Product)

    if category_id:
        query = query.filter(Product.category_id == category_id)
    if keyword:
        query = query.filter(Product.name.contains(keyword))
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)

    total = query.count()
    products = query.order_by(Product.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    inventory_service = InventoryService(db)
    items = []
    for p in products:
        stock_info = inventory_service.get_stock_info(p.id)
        item = ProductResponse.model_validate(p)
        item.current_stock = stock_info.get("total_stock", 0)
        item.near_expiry_stock = sum(
            b["remaining"] for b in stock_info.get("batches", [])
            if b.get("days_to_expiry") is not None and 0 <= b["days_to_expiry"] <= 15
        )
        item.category_name = p.category.name if p.category else None
        items.append(item)

    return ProductListResponse(total=total, items=items)


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """获取商品详情"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    inventory_service = InventoryService(db)
    stock_info = inventory_service.get_stock_info(product_id)

    item = ProductResponse.model_validate(product)
    item.current_stock = stock_info.get("total_stock", 0)
    item.category_name = product.category.name if product.category else None
    return item


@router.post("/products", response_model=ProductResponse)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    """创建商品"""
    # 自动生成编码
    if not data.code:
        import datetime
        data.code = f"SP{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)

    inventory_service = InventoryService(db)
    stock_info = inventory_service.get_stock_info(product.id)

    item = ProductResponse.model_validate(product)
    item.current_stock = stock_info.get("total_stock", 0)
    item.category_name = product.category.name if product.category else None
    return item


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    """更新商品"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    for key, value in data.model_dump().items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)

    inventory_service = InventoryService(db)
    stock_info = inventory_service.get_stock_info(product_id)

    item = ProductResponse.model_validate(product)
    item.current_stock = stock_info.get("total_stock", 0)
    item.category_name = product.category.name if product.category else None
    return item


@router.delete("/products/{product_id}", response_model=MessageResponse)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """删除商品（软删除）"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 检查是否有库存
    inventory_service = InventoryService(db)
    stock = inventory_service.get_product_total_stock(product_id)
    if stock > 0:
        raise HTTPException(status_code=400, detail=f"商品还有库存 {stock}，无法删除。请先处理库存")

    product.is_active = False
    db.commit()
    return MessageResponse(message="商品已停用")
