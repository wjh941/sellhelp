"""
AI生意顾问服务
- 系统内置副食行业赚钱逻辑库
- 结合盈泰自身数据进行AI问答
- 可选接入外部AI（未配置时使用规则引擎）
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import json
import re
import uuid

from ..models.all_models import (
    Product, ProductBatch, SalesOrder, SalesOrderItem,
    Customer, Category, MarketPrice, AIChatHistory, SystemConfig
)
from .inventory_service import InventoryService
from .pricing_service import PricingService


# ========== 副食行业赚钱逻辑库 ==========
BUSINESS_LOGIC_LIBRARY = {
    "引流品逻辑": {
        "description": "粮油走量不赚钱，但用来锁客户。通过低价高频的必需品吸引客户长期合作。",
        "key_points": [
            "粮油、大米、面粉等刚需品定价接近成本价",
            "引流品不单独赚钱，靠它带来的客户购买利润品",
            "保持引流品库存充足，缺货会直接丢失客户",
            "用引流品做促销活动：满赠、特价、捆绑"
        ],
        "example": "进50斤大米成本2.5/斤，卖2.5/斤不赚钱，但客户来买大米时会顺带买调味品、饮料等利润品"
    },
    "利润品逻辑": {
        "description": "调味、礼盒、饮料高利润，重点做毛利。这是真正赚钱的部分。",
        "key_points": [
            "调味品毛利率应在30-50%",
            "礼盒类毛利率应在40-60%",
            "饮料毛利率应在25-35%",
            "高利润品不要轻易降价，保持价格体系稳定"
        ],
        "example": "一瓶生抽成本5元，卖8元，毛利率60%，这才是真正赚钱的商品"
    },
    "大客户锁客逻辑": {
        "description": "晨升膳食如何长期绑定、防止被抢。大客户是核心资产。",
        "key_points": [
            "给大客户专属价，但不要无底线降价",
            "定期回访，了解需求变化",
            "提供增值服务：送货上门、账期灵活、优先供货",
            "建立情感连接：节日问候、生日祝福",
            "定期更新菜单/产品，保持新鲜感"
        ],
        "example": "晨升膳食每月固定采购1万元，给5%专属折扣但要求月结，锁定全年生意额12万"
    },
    "淡旺季套路": {
        "description": "节前备货、节后清库、反向囤货。利用季节规律赚钱。",
        "key_points": [
            "节前3个月开始备货：中秋、春节",
            "节前1个月停止补货，清库存",
            "节后立即清库，避免积压",
            "淡季可以反向囤货（如果资金允许），等旺季涨价"
        ],
        "example": "春节前2个月囤礼盒，春节后礼盒清不出去就特价卖给员工或其他批发商"
    },
    "保质期盈利逻辑": {
        "description": "如何做到零过期损耗。保质期管理直接影响利润。",
        "key_points": [
            "先进先出(FIFO)绝对不能省",
            "建立临期预警：30天/15天双预警",
            "临期品主动促销，不要等过期",
            "按批次进货，不同批次不混放",
            "节日品要提前2个月停止进货"
        ],
        "example": "某饼干6月到期，5月就开始买一送一，比过期扔掉强100倍"
    },
    "定价防内卷套路": {
        "description": "不打价格战，靠结构赚钱。低价竞争是死胡同。",
        "key_points": [
            "宁可少卖，不低价乱卖",
            "建立产品梯度：引流品+常规品+利润品",
            "客户分等级，不同等级不同价",
            "用服务差异化：送货、账期、品质保证",
            "同行低价时，强调品质和服务"
        ],
        "example": "同行卖5元/瓶酱油，你也卖5元就亏了。你卖5.5元但送货上门，客户还是选你"
    },
    "客户分层套路": {
        "description": "散户、小店、食堂不同利润体系。不同客户不同策略。",
        "key_points": [
            "散户：零售价，不降价，保证利润",
            "小店：批发价，薄利多销，靠量赚钱",
            "食堂/工厂：大客户价，锁定长期合同",
            "核心大客户（如晨升）：专属价+增值服务",
            "不要给所有人同一价格，价格就是管理工具"
        ],
        "example": "同一款产品，散户买10元，小店买8元，晨升买7.5元，但晨升月销量是小店的10倍"
    },
    "现金流套路": {
        "description": "少压货、快周转、用周转赚钱而非差价。现金流比利润更重要。",
        "key_points": [
            "库存周转率目标：30天内",
            "滞销品立即处理，不要犹豫",
            "货款尽量快收，账期不要太长",
            "用客户的钱做生意（预收、月结）",
            "定期统计库存占用资金，优化库存结构"
        ],
        "example": "投入10万库存，每月周转2次，相当于20万的流动资金。比囤货等涨价更健康"
    },
    "礼盒淡季清仓": {
        "description": "礼盒淡季压货怎么清不亏钱。节日品过季处理策略。",
        "key_points": [
            "节后立即降价30-50%清仓",
            "打包卖给员工、朋友、其他批发商",
            "拆分散卖：礼盒拆成单品卖",
            "库存礼盒保存好，明年节前提前一个月可以原价卖",
            "如果资金允许，明年可以少量补货，靠去年库存先卖"
        ],
        "example": "春节礼盒节后原价300，节后清150，虽然亏了但拿回了现金流"
    },
    "阶梯锁客模式": {
        "description": "如何设计阶梯锁客模式、月结模式、绑定食堂客户。",
        "key_points": [
            "月结账期：给大客户月结，增加粘性",
            "年返点：年采购满10万返2%，满20万返5%",
            "专属客服：大客户有专人对接",
            "优先供货：旺季保证大客户供货",
            "定制产品：为大客户提供专属规格"
        ],
        "example": "晨升膳食月均采购1万，年返3%即3600元，绑定全年12万交易额"
    }
}


class AIChatService:
    """AI顾问服务"""

    def __init__(self, db: Session):
        self.db = db
        self.inventory = InventoryService(db)
        self.pricing = PricingService(db)

    def ask(self, question: str, context: str = None, session_id: str = None) -> Dict:
        """
        AI问答主入口
        1. 分析问题类型
        2. 匹配行业知识
        3. 结合盈泰数据
        4. 生成回答
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        # 保存用户问题
        self._save_message(session_id, "user", question, context)

        # 分析问题
        answer = self._process_question(question, context)

        # 保存AI回答
        self._save_message(session_id, "assistant", json.dumps(answer, ensure_ascii=False))

        return {
            "answer": answer["text"],
            "session_id": session_id,
            "data_used": answer.get("data_used", {}),
            "logic_matched": answer.get("logic_matched", [])
        }

    def _save_message(self, session_id: str, role: str, content: str, context: str = None):
        """保存对话历史"""
        msg = AIChatHistory(
            session_id=session_id,
            role=role,
            content=content,
            business_context=context
        )
        self.db.add(msg)
        self.db.commit()

    def _process_question(self, question: str, context: str = None) -> Dict:
        """处理问题"""
        # 1. 匹配行业知识
        matched_logic = self._match_business_logic(question)

        # 2. 收集盈泰数据
        business_data = self._collect_business_data(question)

        # 3. 生成回答
        answer = self._generate_answer(question, matched_logic, business_data)

        return answer

    def _match_business_logic(self, question: str) -> List[Dict]:
        """匹配行业知识"""
        matched = []
        question_lower = question.lower()

        keywords_map = {
            "引流品逻辑": ["引流", "走量", "锁客", "粮油", "吸引客户"],
            "利润品逻辑": ["利润", "毛利", "赚钱", "调味", "礼盒", "高利润"],
            "大客户锁客逻辑": ["大客户", "晨升", "膳食", "VIP", "核心客户", "绑定"],
            "淡旺季套路": ["旺季", "淡季", "节前", "备货", "节后", "季节"],
            "保质期盈利逻辑": ["过期", "保质期", "临期", "FIFO", "先进先出", "损耗"],
            "定价防内卷套路": ["定价", "价格战", "内卷", "同行", "降价", "低价"],
            "客户分层套路": ["客户分层", "零售", "批发", "散户", "小店", "分层"],
            "现金流套路": ["现金流", "周转", "资金", "压货", "库存周转"],
            "礼盒淡季清仓": ["礼盒", "清仓", "淡季", "节日", "礼品"],
            "阶梯锁客模式": ["月结", "返点", "阶梯", "锁客", "账期"]
        }

        for logic_name, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in question_lower:
                    matched.append({
                        "logic_name": logic_name,
                        "knowledge": BUSINESS_LOGIC_LIBRARY[logic_name],
                        "matched_keyword": keyword
                    })
                    break

        return matched

    def _collect_business_data(self, question: str) -> Dict:
        """收集盈泰经营数据"""
        data = {}

        # 库存概览
        stock_summary = self.inventory.get_stock_value_summary()
        data["stock"] = stock_summary

        # 临期预警
        expiry_warnings = self.inventory.get_expiry_warnings(warning_days=30)
        data["expiry_warnings"] = expiry_warnings[:10]

        # 客户欠款
        debt_customers = self.db.query(Customer).filter(Customer.current_debt > 0).all()
        data["debt_customers"] = [{
            "name": c.name,
            "debt": c.current_debt,
            "type": c.customer_type
        } for c in debt_customers[:10]]

        # 最近7天销售
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_sales = self.db.query(SalesOrder).filter(
            SalesOrder.sale_date >= seven_days_ago,
            SalesOrder.status == "已完成"
        ).all()
        data["recent_sales"] = {
            "order_count": len(recent_sales),
            "total_amount": sum(o.final_amount for o in recent_sales)
        }

        # 热销商品
        thirty_days_ago = datetime.now() - timedelta(days=30)
        hot_items = self.db.query(
            SalesOrderItem.product_id,
            Product.name,
            func.sum(SalesOrderItem.quantity).label("qty"),
            func.sum(SalesOrderItem.amount).label("amount")
        ).join(Product).join(SalesOrder).filter(
            SalesOrder.sale_date >= thirty_days_ago,
            SalesOrder.status == "已完成"
        ).group_by(SalesOrderItem.product_id).order_by(func.sum(SalesOrderItem.amount).desc()).limit(5).all()

        data["hot_products"] = [{
            "name": r[1],
            "qty": r[2],
            "amount": r[3]
        } for r in hot_items]

        # 滞销商品
        slow_products = self._find_slow_products()
        data["slow_products"] = slow_products[:5]

        return data

    def _find_slow_products(self) -> List[Dict]:
        """找出滞销商品"""
        thirty_days_ago = datetime.now() - timedelta(days=30)
        products = self.db.query(Product).filter(Product.is_active == True).all()
        slow = []

        for p in products:
            stock = self.inventory.get_product_total_stock(p.id)
            if stock <= 0:
                continue

            sales_count = self.db.query(SalesOrderItem).join(SalesOrder).filter(
                SalesOrderItem.product_id == p.id,
                SalesOrder.sale_date >= thirty_days_ago,
                SalesOrder.status == "已完成"
            ).count()

            if sales_count == 0:
                slow.append({
                    "product_id": p.id,
                    "name": p.name,
                    "stock": stock
                })

        return slow[:10]

    def _generate_answer(self, question: str, matched_logic: List[Dict],
                          business_data: Dict) -> Dict:
        """生成AI回答"""
        answer_parts = []

        # 开头：直接回答
        if matched_logic:
            primary_logic = matched_logic[0]
            answer_parts.append(f"关于「{question}」，根据副食行业经验，我的建议是：\n")
            answer_parts.append(f"【核心思路】{primary_logic['knowledge']['description']}")
        else:
            answer_parts.append(f"关于「{question}」，结合盈泰的实际情况，我的分析是：\n")

        # 结合盈泰数据
        data_insights = []

        # 库存情况
        stock_data = business_data.get("stock", {})
        if stock_data.get("total_stock_value", 0) > 0:
            data_insights.append(f"当前库存总值 ¥{stock_data['total_stock_value']:,.2f}")

        # 临期预警
        expiry = business_data.get("expiry_warnings", [])
        if expiry:
            critical = [e for e in expiry if e["warning_level"] == "critical"]
            if critical:
                data_insights.append(f"⚠️ 有{len(critical)}个批次即将过期（15天内）")

        # 滞销品
        slow = business_data.get("slow_products", [])
        if slow:
            names = [s["name"] for s in slow[:3]]
            data_insights.append(f"滞销商品：{', '.join(names)}")

        # 欠款情况
        debts = business_data.get("debt_customers", [])
        if debts:
            total_debt = sum(d["debt"] for d in debts)
            if total_debt > 0:
                data_insights.append(f"客户欠款总额 ¥{total_debt:,.2f}")

        if data_insights:
            answer_parts.append(f"\n【盈泰数据】{'，'.join(data_insights)}")

        # 匹配到的知识要点
        if matched_logic:
            answer_parts.append("\n【实操建议】")
            for logic in matched_logic:
                key_points = logic["knowledge"]["key_points"][:4]
                for i, point in enumerate(key_points, 1):
                    answer_parts.append(f"  {i}. {point}")

                if logic["knowledge"].get("example"):
                    answer_parts.append(f"\n  📌 实际案例：{logic['knowledge']['example']}")

        # 针对性建议
        answer_parts.append("\n【立即行动】")
        specific_actions = self._get_specific_advice(question, business_data, matched_logic)
        for action in specific_actions:
            answer_parts.append(f"  ▶ {action}")

        return {
            "text": "\n".join(answer_parts),
            "data_used": business_data,
            "logic_matched": [l["logic_name"] for l in matched_logic]
        }

    def _get_specific_advice(self, question: str, business_data: Dict,
                              matched_logic: List[Dict]) -> List[str]:
        """获取针对性建议"""
        advice = []
        question_lower = question.lower()

        # 保质期相关
        if any(kw in question_lower for kw in ["过期", "保质期", "临期", "损耗"]):
            expiry = business_data.get("expiry_warnings", [])
            if expiry:
                critical = [e for e in expiry if e["warning_level"] == "critical"]
                warning = [e for e in expiry if e["warning_level"] == "warning"]

                if critical:
                    products = list(set(e["product_name"] for e in critical))
                    advice.append(f"立即处理：{', '.join(products)}（15天内过期）")
                if warning:
                    products = list(set(e["product_name"] for e in warning))
                    advice.append(f"准备清库：{', '.join(products)}（30天内过期）")

                advice.append("设置临期特价专区，买赠或捆绑销售")
                advice.append("下次进货时减少采购量，按实际销量备货")

        # 定价相关
        elif any(kw in question_lower for kw in ["定价", "价格", "定价", "不亏", "定价"]):
            advice.append("对重点商品进行AI定价分析")
            advice.append("建立三档价格体系：零售/批发/VIP")
            advice.append("定期审查价格，不要轻易降价")

        # 客户相关
        elif any(kw in question_lower for kw in ["客户", "跑", "同行", "留住"]):
            advice.append("对核心客户建立定期回访机制")
            advice.append("分析客户采购数据，了解需求变化")
            advice.append("提供增值服务：送货、账期、优先供货")

        # 库存相关
        elif any(kw in question_lower for kw in ["库存", "压货", "资金"]):
            slow = business_data.get("slow_products", [])
            if slow:
                names = [s["name"] for s in slow[:3]]
                advice.append(f"清仓处理：{', '.join(names)}")

            advice.append("优化进货量，按近30天销量备货")
            advice.append("设置安全库存，避免缺货和积压")

        # 礼盒/节日
        elif any(kw in question_lower for kw in ["礼盒", "节日", "中秋", "春节"]):
            advice.append("节前3个月开始备货，节前1个月停止补货")
            advice.append("节后立即清库，不要等过期")
            advice.append("礼盒可拆分散卖，或卖给批发商回笼资金")

        # 通用建议
        if not advice:
            advice.append("查看本周经营分析报告，了解整体情况")
            advice.append("对热销商品保持充足库存")
            advice.append("对滞销商品制定清仓计划")

        return advice

    def get_chat_history(self, session_id: str) -> List[Dict]:
        """获取会话历史"""
        messages = self.db.query(AIChatHistory).filter(
            AIChatHistory.session_id == session_id
        ).order_by(AIChatHistory.created_at.asc()).all()

        return [{
            "role": m.role,
            "content": m.content,
            "created_at": str(m.created_at) if m.created_at else None
        } for m in messages]

    def get_sessions_list(self) -> List[Dict]:
        """获取所有会话列表"""
        # 获取每个会话的最后一条消息
        subquery = self.db.query(
            AIChatHistory.session_id,
            func.max(AIChatHistory.created_at).label("last_time")
        ).group_by(AIChatHistory.session_id).subquery()

        sessions = self.db.query(
            AIChatHistory.session_id,
            AIChatHistory.content,
            AIChatHistory.created_at
        ).join(
            subquery,
            AIChatHistory.session_id == subquery.c.session_id
        ).filter(
            AIChatHistory.created_at == subquery.c.last_time
        ).order_by(AIChatHistory.created_at.desc()).all()

        return [{
            "session_id": s[0],
            "last_message": s[1][:100] if s[1] else "",
            "updated_at": str(s[2]) if s[2] else None
        } for s in sessions]
