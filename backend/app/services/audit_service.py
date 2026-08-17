from sqlalchemy.orm import Session

from ..models.all_models import AuditLog


def record_audit(
    db: Session,
    *,
    user_id: int | None,
    client_ip: str | None,
    operation_type: str,
    operation_detail: str,
    status_code: int,
) -> None:
    try:
        db.add(
            AuditLog(
                user_id=user_id,
                client_ip=client_ip,
                operation_type=operation_type,
                operation_detail=operation_detail,
                status_code=status_code,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
