from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.main import decide_approval, orchestrator
from app.models import ApprovalDecision, AutomationRequest
from app.schemas import ApprovalInput
from services.servicenow_sim.agent import run_pending_cases
from services.servicenow_sim.service import create_case, get_case_by_number


def _create_pending_approval_case(db: Session) -> tuple[str, str]:
    case = create_case(
        db,
        short_description='Eliminar usuario qa_sync_case en ol9server1',
        request_type='delete_user',
        params={'username': 'qa_sync_case'},
        targets=['ol9server1'],
        requested_by='qa.sync',
    )
    result = run_pending_cases(db, orchestrator=orchestrator, limit=200)
    assert result.processed >= 1

    updated_case = get_case_by_number(db, case.number)
    assert updated_case is not None
    assert updated_case.state == 'awaiting_approval'
    assert updated_case.automation_request_id is not None
    return updated_case.number, updated_case.automation_request_id


def test_approval_decision_syncs_case_to_resolved_when_approved() -> None:
    with SessionLocal() as db:
        case_number, request_id = _create_pending_approval_case(db)

        approval = db.execute(
            select(ApprovalDecision).where(ApprovalDecision.request_id == request_id)
        ).scalar_one_or_none()
        assert approval is not None
        assert approval.status == 'pending'

        response = decide_approval(
            request_id,
            ApprovalInput(approver='qa.approver', decision='approve', comment='ok para ejecutar'),
            db,
        )
        assert response.status == 'approved'

        request = db.execute(select(AutomationRequest).where(AutomationRequest.id == request_id)).scalar_one()
        assert request.status in {'executed', 'validated'}

        updated_case = get_case_by_number(db, case_number)
        assert updated_case is not None
        assert updated_case.state == 'resolved'
        assert updated_case.execution_id == request.execution_id


def test_approval_decision_syncs_case_to_manual_attention_when_rejected() -> None:
    with SessionLocal() as db:
        case_number, request_id = _create_pending_approval_case(db)

        response = decide_approval(
            request_id,
            ApprovalInput(approver='qa.approver', decision='reject', comment='riesgo no aceptado'),
            db,
        )
        assert response.status == 'rejected'

        request = db.execute(select(AutomationRequest).where(AutomationRequest.id == request_id)).scalar_one()
        assert request.status == 'rejected'

        updated_case = get_case_by_number(db, case_number)
        assert updated_case is not None
        assert updated_case.state == 'needs_manual_attention'
        assert 'Rechazado por' in str(updated_case.resolution_notes or '')
