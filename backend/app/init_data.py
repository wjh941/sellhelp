"""
初始化脚本 - 创建默认分类和示例数据
运行方式: python -m app.init_data
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, init_db
from app.models.all_models import Category, Supplier, Customer

# 创建数据库表

db = SessionLocal()


def init_categories():
    """初始化商品分类"""
    default_categories = [
        {"name": "粮油", "sort_order": 1},
        {"name": "调味", "sort_order": 2},
        {"name": "饮料", "sort_order": 3},
        {"name": "零食", "sort_order": 4},
        {"name": "礼盒", "sort_order": 5},
        {"name": "节日品", "sort_order": 6},
        {"name": "日杂", "sort_order": 7}
    ]

    for cat_data in default_categories:
        existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
        if not existing:
            cat = Category(
                name=cat_data["name"],
                sort_order=cat_data["sort_order"]
            )
            db.add(cat)
            print(f"  ✓ 创建分类: {cat_data['name']}")
        else:
            print(f"  - 分类已存在: {cat_data['name']}")


def init_default_supplier():
    """创建默认供应商"""
    existing = db.query(Supplier).filter(Supplier.name == "默认供应商").first()
    if not existing:
        supplier = Supplier(
            name="默认供应商",
            contact_person="待填写",
            phone="待填写",
            address="待填写",
            payment_term="现金结算",
            cooperation_status="正常合作",
            remark="请后续完善供应商信息"
        )
        db.add(supplier)
        print("  ✓ 创建默认供应商: 默认供应商")


def init_default_customers():
    """创建默认客户"""
    default_customers = [
        {
            "name": "晨升膳食",
            "customer_type": "VIP",
            "is_vip": True,
            "contact_person": "待填写",
            "phone": "待填写",
            "address": "待填写",
            "credit_limit": 50000,
            "remark": "核心大客户 - 食堂配送"
        },
        {
            "name": "零售散客",
            "customer_type": "散户",
            "is_vip": False,
            "credit_limit": 0,
            "remark": "普通零售客户"
        }
    ]

    for cust_data in default_customers:
        existing = db.query(Customer).filter(Customer.name == cust_data["name"]).first()
        if not existing:
            customer = Customer(**cust_data)
            db.add(customer)
            print(f"  ✓ 创建客户: {cust_data['name']}")
        else:
            print(f"  - 客户已存在: {cust_data['name']}")


def main():
    init_db()
    print("=" * 50)
    print("盈泰副食贸易管理系统 - 数据初始化")
    print("=" * 50)
    print()

    print("📦 初始化商品分类...")
    init_categories()

    print("\n🏭 初始化供应商...")
    init_default_supplier()

    print("\n👥 初始化客户...")
    init_default_customers()

    db.commit()
    print("\n" + "=" * 50)
    print("✅ 初始化完成！")
    print("=" * 50)
    print("\n下一步：")
    print("  1. 启动后端: uvicorn app.main:app --host 0.0.0.0 --port 8001")
    print("  2. 启动前端: cd frontend && npm run dev")
    print("  3. 访问系统: http://localhost:8080")
    print()


if __name__ == "__main__":
    main()
