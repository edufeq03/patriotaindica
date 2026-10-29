import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.models.business import Business
from backend.app.models.jobs import JobOpening, JobReviewLog
from backend.app.models.user import User
from backend.app.schemas.jobs import JobClose, JobCreate, JobUpdate
from backend.app.services.job_moderation import (
    check_job_content,
    normalize_for_moderation,
)
from backend.app.services.job_service import (
    close_job_opening,
    create_job_opening,
    renew_job_opening,
    toggle_job_pause,
    update_job_opening,
)
from backend.app.services.job_worker import expire_overdue_jobs


# ------------------------------------------------------------------------------
# 1. Testes de Moderação e Validação de Conteúdo (Seção 5 e 13)
# ------------------------------------------------------------------------------

def test_job_moderation_discrimination_blocked():
    """Garante bloqueio de termos discriminatórios com mensagem educativa."""
    res1 = check_job_content("Atendente de Balcão", "Exige-se boa aparência e simpatia.")
    assert res1.is_blocked is True
    assert res1.block_category == "discriminacao"
    assert "Não é permitido exigir idade, sexo, estado civil, aparência" in res1.educational_message

    res2 = check_job_content("Vendedora Loja", "Apenas mulheres solteiras e sem filhos.")
    assert res2.is_blocked is True
    assert res2.block_category == "discriminacao"


def test_job_moderation_political_religious_conviction_blocked():
    """Garante bloqueio de exigência de convicção política ou religiosa."""
    res1 = check_job_content("Assistente Administrativo", "Perfil de direita e cristão.")
    assert res1.is_blocked is True
    assert res1.block_category == "conviccao"

    res2 = check_job_content("Auxiliar", "Alinhado politicamente com nosso partido.")
    assert res2.is_blocked is True
    assert res2.block_category == "conviccao"


def test_job_moderation_scam_fee_blocked():
    """Garante bloqueio de cobrança de taxa de inscrição ou golpe multinível."""
    res1 = check_job_content("Digitador Home Office", "Taxa de inscrição de R$ 50 para material.")
    assert res1.is_blocked is True
    assert res1.block_category == "golpe"
    assert "A candidatura a vagas de emprego no Patriota Indica deve ser 100% gratuita" in res1.educational_message

    res2 = check_job_content("Trabalhe de casa ganhando", "Renda extra garantida sem experiência.")
    assert res2.is_blocked is True
    assert res2.block_category == "golpe"


def test_job_moderation_apprentice_stage_exception():
    """Termos de idade são permitidos em estágio e aprendiz, mas bloqueados em CLT."""
    # Em CLT: bloqueado
    clt_res = check_job_content("Auxiliar de Almoxarifado", "Vaga para jovem até 25 anos.", contract_type="clt")
    assert clt_res.is_blocked is True

    # Em Jovem Aprendiz: permitido por lei
    aprendiz_res = check_job_content("Jovem Aprendiz", "Vaga para jovem até 25 anos.", contract_type="aprendiz")
    assert aprendiz_res.is_blocked is False

    # Em Estágio: permitido por lei
    estagio_res = check_job_content("Estágio em TI", "Oportunidade para jovem estudante.", contract_type="estagio")
    assert estagio_res.is_blocked is False


def test_job_moderation_leet_speak_detection():
    """Garante detecção de evasões por leet speak (0->o, 1->i, 3->e, 4->a)."""
    assert normalize_for_moderation("B0A   APARÊNCIA") == "boa aparencia"
    res = check_job_content("Recepcionista", "Exige b0a aparencia.")
    assert res.is_blocked is True
    assert res.block_category == "discriminacao"


def test_job_moderation_clean_job_passes():
    """Vaga limpa e profissional passa sem bloqueios."""
    res = check_job_content(
        title="Eletricista de Manutenção",
        description="Atividades de manutenção predial e industrial. Horário de segunda a sexta, das 8h às 17h.",
        contract_type="clt",
    )
    assert res.is_blocked is False
    assert res.is_review is False
    assert len(res.flags) == 0


# ------------------------------------------------------------------------------
# 2. Testes de Schemas e Bloqueio de Mass Assignment (Seção 7 e 11)
# ------------------------------------------------------------------------------

def test_job_create_schema_forbids_extra_privileged_fields():
    """Garante que o dono não consegue injetar status, admin_hold ou datas."""
    with pytest.raises(ValidationError):
        JobCreate(
            title="Mecânico Automotivo",
            contract_type="clt",
            status="active",  # Campo proibido
        )

    with pytest.raises(ValidationError):
        JobCreate(
            title="Mecânico Automotivo",
            contract_type="clt",
            admin_hold=True,  # Campo proibido
        )


def test_job_create_schema_text_sanitization():
    """Garante sanitização de URLs, telefones e repetições no título."""
    with pytest.raises(ValidationError):
        JobCreate(title="Mecânico acesse https://site.com", contract_type="clt")

    with pytest.raises(ValidationError):
        JobCreate(title="Mecânico ligue 19999998888", contract_type="clt")

    with pytest.raises(ValidationError):
        JobCreate(title="Mecânico aaaaaa", contract_type="clt")


# ------------------------------------------------------------------------------
# 3. Testes de Serviço e Regras de Negócio (Seção 4, 6 e 13)
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_creation_limit_enforced():
    """Garante que a 4ª vaga ativa na mesma empresa gera 409 Conflict."""
    mock_db = AsyncMock()
    # Simula contagem atual de 3 vagas ativas
    mock_scalar = MagicMock()
    mock_scalar.scalar.return_value = 3
    mock_db.execute.return_value = mock_scalar

    biz = Business(id=uuid.uuid4(), name="Oficina Patriota", status="approved")
    user = User(id=uuid.uuid4(), name="Dono Oficina", role="owner")
    payload = JobCreate(title="Auxiliar de Mecânica", contract_type="clt")

    with pytest.raises(HTTPException) as exc_info:
        await create_job_opening(business=biz, user=user, payload=payload, db=mock_db)
    assert exc_info.value.status_code == 409
    assert "Limite de 3 vagas ativas" in exc_info.value.detail


@pytest.mark.asyncio
async def test_job_creation_unapproved_business_rejected():
    """Empresa não aprovada na curadoria não pode publicar vagas."""
    mock_db = AsyncMock()
    biz = Business(id=uuid.uuid4(), name="Empresa Pendente", status="pending_review")
    user = User(id=uuid.uuid4(), name="Dono", role="owner")
    payload = JobCreate(title="Atendente", contract_type="clt")

    with pytest.raises(HTTPException) as exc_info:
        await create_job_opening(business=biz, user=user, payload=payload, db=mock_db)
    assert exc_info.value.status_code == 400
    assert "Apenas empresas aprovadas" in exc_info.value.detail


@pytest.mark.asyncio
async def test_job_lifecycle_pause_and_resume():
    """Garante pausa pelo dono e impedimento de reativação se houver admin_hold."""
    mock_db = AsyncMock()
    user = User(id=uuid.uuid4(), role="owner")
    job = JobOpening(
        id=uuid.uuid4(),
        title="Padeiro",
        status="active",
        owner_paused=False,
        admin_hold=False,
    )

    # Pausa com sucesso
    paused_job = await toggle_job_pause(job, user, pause=True, db=mock_db)
    assert paused_job.owner_paused is True

    # Reativa com sucesso
    resumed_job = await toggle_job_pause(job, user, pause=False, db=mock_db)
    assert resumed_job.owner_paused is False

    # Se estiver com admin_hold, dono não pode reativar
    job.admin_hold = True
    job.owner_paused = True
    with pytest.raises(HTTPException) as exc:
        await toggle_job_pause(job, user, pause=False, db=mock_db)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_job_renewal_max_limit():
    """Garante que a vaga só pode ser renovada até 2 vezes (30 dias cada)."""
    mock_db = AsyncMock()
    user = User(id=uuid.uuid4(), role="owner")
    job = JobOpening(
        id=uuid.uuid4(),
        title="Marceneiro",
        status="active",
        renewed_count=2,  # Já atingiu o teto de 2 renovações
        admin_hold=False,
    )

    with pytest.raises(HTTPException) as exc:
        await renew_job_opening(job, user, db=mock_db)
    assert exc.value.status_code == 409
    assert "limite máximo de 2 renovações" in exc.value.detail


@pytest.mark.asyncio
async def test_job_worker_expires_overdue_jobs():
    """Worker expira vagas cuja data de validade já passou."""
    mock_db = AsyncMock()
    now = datetime.now(timezone.utc)
    overdue_job = JobOpening(
        id=uuid.uuid4(),
        title="Vaga Vencida",
        status="active",
        expires_at=now - timedelta(days=1),
    )

    mock_scalar = MagicMock()
    mock_scalar.scalars.return_value.all.return_value = [overdue_job]
    mock_db.execute.return_value = mock_scalar

    expired_count = await expire_overdue_jobs(mock_db)
    assert expired_count == 1
    assert overdue_job.status == "expired"


@pytest.mark.asyncio
async def test_admin_decision_approve_reject_and_hold():
    """Valida decisões de moderação pelo administrador (T-V2.1)."""
    from backend.app.services.job_service import admin_review_job

    mock_db = AsyncMock()
    admin = User(id=uuid.uuid4(), role="admin")
    job = JobOpening(
        id=uuid.uuid4(),
        title="Torneiro Mecânico",
        status="pending_review",
        admin_hold=False,
    )

    # 1. Aprovação
    await admin_review_job(job, admin, action="approve", reason_code=None, note="OK", db=mock_db)
    assert job.status == "active"
    assert job.published_at is not None
    assert job.expires_at is not None
    assert job.admin_hold is False

    # 2. Bloqueio (Hold)
    await admin_review_job(job, admin, action="hold", reason_code="denuncia", note="Sob análise", db=mock_db)
    assert job.admin_hold is True

    # 3. Liberação (Release)
    await admin_review_job(job, admin, action="release", reason_code=None, note="Liberado", db=mock_db)
    assert job.admin_hold is False

    # 4. Rejeição
    await admin_review_job(job, admin, action="reject", reason_code="conteudo_inadequado", note="Reprovada", db=mock_db)
    assert job.status == "rejected"
    assert job.rejection_code == "conteudo_inadequado"


def test_job_public_visibility_property():
    """Valida a regra de visibilidade pública (P1, Seção 4)."""
    now = datetime.now(timezone.utc)
    business = Business(id=uuid.uuid4(), status="approved", owner_paused=False)

    # Vaga ativa regular
    job = JobOpening(
        id=uuid.uuid4(),
        status="active",
        owner_paused=False,
        admin_hold=False,
        expires_at=now + timedelta(days=10),
        business=business,
    )
    assert job.is_publicly_visible is True

    # Se pausada pelo dono -> invisível
    job.owner_paused = True
    assert job.is_publicly_visible is False
    job.owner_paused = False

    # Se em admin_hold -> invisível
    job.admin_hold = True
    assert job.is_publicly_visible is False
    job.admin_hold = False

    # Se expirada -> invisível
    job.expires_at = now - timedelta(days=1)
    assert job.is_publicly_visible is False
    job.expires_at = now + timedelta(days=10)

    # Se empresa suspensa -> invisível
    business.status = "suspended"
    assert job.is_publicly_visible is False


@pytest.mark.asyncio
async def test_notify_expiring_jobs_worker():
    """Valida identificação de vagas a expirar em até 3 dias (T-V3.4)."""
    from backend.app.services.job_worker import notify_expiring_jobs

    mock_db = AsyncMock()
    now = datetime.now(timezone.utc)
    business = Business(id=uuid.uuid4(), name="Oficina do Zé", status="approved")
    expiring_job = JobOpening(
        id=uuid.uuid4(),
        title="Mecânico Geral",
        status="active",
        expires_at=now + timedelta(days=2),
        renewed_count=0,
        business=business,
    )

    mock_result = MagicMock()
    mock_result.all.return_value = [(expiring_job, business)]
    mock_db.execute.return_value = mock_result

    count = await notify_expiring_jobs(mock_db)
    assert count == 1


