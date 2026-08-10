"""
周报与AI顾问 API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from ..database import get_db
from ..models.all_models import WeeklyReport, AIChatHistory
from ..schemas.all_schemas import (
    WeeklyReportResponse,
    AIQuestionRequest, AIAnswerResponse, MessageResponse
)
from ..services.report_service import ReportService
from ..services.ai_service import AIChatService

router = APIRouter(prefix="/api", tags=["周报与AI顾问"])

# ========== 经营分析周报 ==========

@router.post("/reports/generate", response_model=WeeklyReportResponse)
def generate_weekly_report(
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """生成周度经营分析报告"""
    report_service = ReportService(db)
    target_date = date.fromisoformat(end_date) if end_date else None
    report = report_service.generate_weekly_report(target_date)
    return WeeklyReportResponse.model_validate(report)


@router.get("/reports/latest", response_model=WeeklyReportResponse)
def get_latest_report(db: Session = Depends(get_db)):
    """获取最新周报"""
    report_service = ReportService(db)
    report = report_service.get_latest_report()
    if not report:
        raise HTTPException(status_code=404, detail="暂无周报，请先生成")
    return WeeklyReportResponse.model_validate(report)


@router.get("/reports", response_model=List[WeeklyReportResponse])
def list_reports(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """获取周报历史"""
    report_service = ReportService(db)
    reports = report_service.get_reports_history(limit)
    return [WeeklyReportResponse.model_validate(r) for r in reports]


@router.get("/reports/{report_id}", response_model=WeeklyReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    """获取单份周报详情"""
    report = db.query(WeeklyReport).filter(WeeklyReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="周报不存在")
    return WeeklyReportResponse.model_validate(report)


# ========== AI生意顾问 ==========

@router.post("/ai-chat/ask", response_model=AIAnswerResponse)
def ai_ask(data: AIQuestionRequest, db: Session = Depends(get_db)):
    """AI生意顾问问答"""
    ai_service = AIChatService(db)
    result = ai_service.ask(
        question=data.question,
        context=data.context,
        session_id=data.session_id
    )
    return AIAnswerResponse(
        answer=result["answer"],
        session_id=result["session_id"],
        data_used=result.get("data_used"),
        logic_matched=result.get("logic_matched", [])
    )


@router.get("/ai-chat/sessions", response_model=List[dict])
def list_ai_sessions(db: Session = Depends(get_db)):
    """获取AI对话会话列表"""
    ai_service = AIChatService(db)
    return ai_service.get_sessions_list()


@router.get("/ai-chat/sessions/{session_id}", response_model=List[dict])
def get_ai_session(session_id: str, db: Session = Depends(get_db)):
    """获取AI对话会话历史"""
    ai_service = AIChatService(db)
    history = ai_service.get_chat_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="会话不存在")
    return history


@router.delete("/ai-chat/sessions/{session_id}", response_model=MessageResponse)
def delete_ai_session(session_id: str, db: Session = Depends(get_db)):
    """删除AI对话会话"""
    messages = db.query(AIChatHistory).filter(AIChatHistory.session_id == session_id).all()
    if not messages:
        raise HTTPException(status_code=404, detail="会话不存在")
    for msg in messages:
        db.delete(msg)
    db.commit()
    return MessageResponse(message="会话已删除")
