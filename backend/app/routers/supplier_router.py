"""
供应商管理 API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.all_models import Supplier
from ..schemas.all_schemas import (
    SupplierCreate, SupplierUpdate, SupplierResponse, MessageResponse
)

router = APIRouter(prefix="/api/suppliers", tags=["供应商管理"])


@router.get("", response_model=List[SupplierResponse])
def list_suppliers(
    keyword: Optional[str] = None,
    cooperation_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取供应商列表"""
    query = db.query(Supplier)
    if keyword:
        query = query.filter(Supplier.name.contains(keyword))
    if cooperation_status:
        query = query.filter(Supplier.cooperation_status == cooperation_status)
    return query.order_by(Supplier.id.desc()).all()


@router.post("", response_model=SupplierResponse)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db)):
    """创建供应商"""
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    """获取供应商详情"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="供应商不存在")
    return supplier


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(supplier_id: int, data: SupplierUpdate, db: Session = Depends(get_db)):
    """更新供应商"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="供应商不存在")
    for key, value in data.model_dump().items():
        setattr(supplier, key, value)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", response_model=MessageResponse)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    """删除供应商"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="供应商不存在")
    if supplier.purchase_records:
        raise HTTPException(status_code=400, detail="该供应商有入库记录，无法删除")
    db.delete(supplier)
    db.commit()
    return MessageResponse(message="删除成功")
