import hashlib
import hmac
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.business import Business
from backend.app.models.payment import Payment
from backend.app.models.subscription import Plan, Referral, Subscription
from backend.app.models.user import User

logger = logging.getLogger("patriotaindica.payments")
router = APIRouter()

# Fallback inicial seguro para execução de testes unitários com mock sem migração aplicada
DEFAULT_PLANS_SEED = [
    {
        "id": "mensal",
        "name": "Plano Mensal",
        "price_cents": 1500,
        "monthly_equivalent_cents": 1500,
        "duration_months": 1,
        "description": "Flexibilidade total, sem fidelidade. Cancele quando quiser.",
        "badge": "Sem Fidelidade",
        "is_featured": False,
        "search_priority": 10,
        "max_categories": 3,
        "max_photos": 10,
        "has_leads_access": True,
        "has_metrics_access": True,
        "has_banner_access": False,
    },
    {
        "id": "semestral",
        "name": "Plano Semestral",
        "price_cents": 7794,
        "monthly_equivalent_cents": 1299,
        "duration_months": 6,
        "description": "6 meses garantidos de visibilidade na sua região com 13% de economia.",
        "badge": "Economize 13%",
        "is_featured": False,
        "search_priority": 20,
        "max_categories": 5,
        "max_photos": 15,
        "has_leads_access": True,
        "has_metrics_access": True,
        "has_banner_access": False,
    },
    {
        "id": "anual",
        "name": "Plano Anual",
        "price_cents": 11988,
        "monthly_equivalent_cents": 999,
        "duration_months": 12,
        "description": "O mais escolhido pelos empresários patriotas: menos de R$ 0,33 por dia (em até 12x de R$ 9,99).",
        "badge": "Mais Popular • 33% OFF",
        "is_featured": True,
        "search_priority": 30,
        "max_categories": 10,
        "max_photos": 20,
        "has_leads_access": True,
        "has_metrics_access": True,
        "has_banner_access": True,
    },
]


def _format_plan_dto(p: Any) -> Dict[str, Any]:
    """Converte um registro da tabela Plan ou dicionário de seed em DTO serializável."""
    if isinstance(p, dict):
        price_cents = p["price_cents"]
        monthly_cents = p["monthly_equivalent_cents"]
        is_feat = p.get("is_featured", False)
        return {
            "id": p["id"],
            "name": p["name"],
            "price_cents": price_cents,
            "price_formatted": f"R$ {price_cents / 100:.2f}".replace(".", ","),
            "monthly_equivalent": f"R$ {monthly_cents / 100:.2f}".replace(".", ","),
            "duration_months": p["duration_months"],
            "description": p.get("description", ""),
            "badge": p.get("badge", ""),
            "is_featured": is_feat,
            "popular": is_feat,
            "search_priority": p.get("search_priority", 1),
            "max_categories": p.get("max_categories", 1),
            "max_photos": p.get("max_photos", 3),
            "has_leads_access": p.get("has_leads_access", False),
            "has_metrics_access": p.get("has_metrics_access", False),
            "has_banner_access": p.get("has_banner_access", False),
        }

    price_cents = getattr(p, "price_cents", 0)
    monthly_cents = getattr(p, "monthly_equivalent_cents", price_cents)
    is_feat = getattr(p, "is_featured", False)
    return {
        "id": p.id,
        "name": p.name,
        "price_cents": price_cents,
        "price_formatted": f"R$ {price_cents / 100:.2f}".replace(".", ","),
        "monthly_equivalent": f"R$ {monthly_cents / 100:.2f}".replace(".", ","),
        "duration_months": p.duration_months,
        "description": getattr(p, "description", "") or "",
        "badge": getattr(p, "badge", "") or "",
        "is_featured": is_feat,
        "popular": is_feat,
        "search_priority": getattr(p, "search_priority", 1),
        "max_categories": getattr(p, "max_categories", 1),
        "max_photos": getattr(p, "max_photos", 3),
        "has_leads_access": getattr(p, "has_leads_access", False),
        "has_metrics_access": getattr(p, "has_metrics_access", False),
        "has_banner_access": getattr(p, "has_banner_access", False),
    }


def verify_mercadopago_signature(
    x_signature: Optional[str],
    x_request_id: Optional[str],
    data_id: Optional[str],
    secret: Optional[str],
) -> bool:
    """
    T4.3: Validação criptográfica rigorosa do cabeçalho x-signature (HMAC-SHA256).
    manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
    """
    if not secret:
        return True
    if not x_signature:
        return False

    parts: Dict[str, str] = {}
    for item in re.split(r"[,;]", x_signature):
        if "=" in item:
            k, v = item.strip().split("=", 1)
            parts[k.strip()] = v.strip()

    ts = parts.get("ts")
    v1 = parts.get("v1")
    if not ts or not v1:
        return False

    manifest = f"id:{data_id or ''};request-id:{x_request_id or ''};ts:{ts};"
    calculated = hmac.new(secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(calculated, v1)


class CreatePreferenceRequest(BaseModel):
    plan_id: str = Field(..., pattern="^(mensal|semestral|anual)$")
    business_id: Optional[UUID] = None


@router.get("/plans")
async def get_plans(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    T4.1: Retorna os planos diretamente da tabela 'plans' no banco de dados
    como fonte única da verdade, com ordenação por valor em centavos.
    """
    try:
        stmt = select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_cents.asc())
        db_plans = (await db.execute(stmt)).scalars().all()
        if db_plans:
            return [_format_plan_dto(p) for p in db_plans]
    except Exception as exc:
        logger.warning("Falha ao buscar planos no banco de dados, utilizando seed padrão: %s", exc)

    return [_format_plan_dto(p) for p in DEFAULT_PLANS_SEED]


@router.get("/my-subscription")
async def get_my_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    T4.2: Consulta o status da assinatura do proprietário com modelagem completa de ciclo de vida:
    - active: dentro da vigência paga
    - grace_period: 3 dias de carência com benefícios mantidos
    - expired: expirado além do prazo de carência
    - canceled: cancelado ou estornado
    """
    stmt = (
        select(Subscription)
        .where(Subscription.owner_user_id == current_user.id)
        .order_by(Subscription.current_period_end.desc())
    )
    sub = (await db.execute(stmt)).scalars().first()

    now = datetime.now(timezone.utc)
    current_status = "none"
    is_active = False

    if sub:
        if sub.status == "canceled":
            current_status = "canceled"
            is_active = False
        elif sub.current_period_end >= now:
            current_status = "active"
            is_active = True
        elif sub.current_period_end >= (now - timedelta(days=3)):
            current_status = "grace_period"
            is_active = True
        else:
            current_status = "expired"
            is_active = False

    days_remaining = max(0, (sub.current_period_end - now).days) if (sub and is_active) else 0

    # Buscar dados do plano contratado
    plan_data = None
    if sub and getattr(sub, "plan", None):
        plan_data = _format_plan_dto(sub.plan)
    elif sub and sub.plan_id:
        match = next((p for p in DEFAULT_PLANS_SEED if p["id"] == sub.plan_id), None)
        if match:
            plan_data = _format_plan_dto(match)


    # Buscar empresas do dono para obter o código de indicação
    biz_stmt = select(Business).where(Business.owner_user_id == current_user.id)
    businesses = (await db.execute(biz_stmt)).scalars().all()

    primary_biz = businesses[0] if businesses else None
    referral_code = None
    if primary_biz:
        ref_candidate = primary_biz.referral_code
        if ref_candidate and ref_candidate.strip() and ref_candidate.strip().lower() not in ("none", "null"):
            referral_code = ref_candidate.strip().upper()
        else:
            referral_code = f"PAT-{str(primary_biz.id).replace('-', '')[:6].upper()}"
            primary_biz.referral_code = referral_code
            await db.commit()
    else:
        referral_code = f"PAT-{str(current_user.id).replace('-', '')[:6].upper()}"

    # Estatísticas do programa Indique e Ganhe
    ref_count_stmt = select(func.count(Referral.id)).where(Referral.referrer_user_id == current_user.id)
    total_referred = (await db.execute(ref_count_stmt)).scalar() or 0

    rewarded_count_stmt = select(func.count(Referral.id)).where(
        Referral.referrer_user_id == current_user.id,
        Referral.status == "rewarded",
    )
    total_rewarded = (await db.execute(rewarded_count_stmt)).scalar() or 0

    return {
        "has_subscription": sub is not None,
        "is_active": is_active,
        "status": current_status,
        "plan_id": sub.plan_id if sub else None,
        "plan_name": plan_data["name"] if plan_data else None,
        "plan": plan_data,
        "current_period_end": sub.current_period_end.isoformat() if sub else None,
        "days_remaining": days_remaining,
        "billing_mode": settings.BILLING_MODE,
        "businesses_count": len(businesses),
        "referral_code": referral_code,
        "referral_link": f"https://patriotaindica.com.br/?ref={referral_code}",
        "referral_stats": {
            "total_referred": total_referred,
            "total_rewarded": total_rewarded,
            "free_months_earned": total_rewarded,
        },
    }


@router.post("/create-preference")
async def create_mercadopago_preference(
    payload: CreatePreferenceRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    T4.1 & T4.4: Gera link de checkout do Mercado Pago buscando dados do plano no DB
    e usando ESTRITAMENTE a variável de ambiente PUBLIC_APP_URL (sem injeção de Origin).
    """
    # 1. T4.1: Obter plano oficial do banco de dados
    plan_record = None
    try:
        p_stmt = select(Plan).where(Plan.id == payload.plan_id, Plan.is_active.is_(True))
        plan_record = (await db.execute(p_stmt)).scalars().first()
    except Exception:
        pass

    if plan_record:
        plan = _format_plan_dto(plan_record)
    else:
        fallback = next((p for p in DEFAULT_PLANS_SEED if p["id"] == payload.plan_id), None)
        if not fallback:
            raise HTTPException(status_code=400, detail="Plano inválido.")
        plan = _format_plan_dto(fallback)

    # 2. T4.4: URLs de retorno seguras oriundas estritamente de PUBLIC_APP_URL
    app_url = settings.PUBLIC_APP_URL.rstrip("/")
    unit_price = float(plan["price_cents"]) / 100.0
    mp_token = settings.MERCADO_PAGO_ACCESS_TOKEN

    if mp_token:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                mp_payload = {
                    "items": [
                        {
                            "id": plan["id"],
                            "title": f"Patriota Indica - {plan['name']}",
                            "description": plan["description"],
                            "quantity": 1,
                            "currency_id": "BRL",
                            "unit_price": unit_price,
                        }
                    ],
                    "payer": {
                        "name": current_user.name,
                        "email": current_user.email,
                    },
                    "back_urls": {
                        "success": f"{app_url}/painel-empresa?status=success",
                        "failure": f"{app_url}/painel-empresa?status=failure",
                        "pending": f"{app_url}/painel-empresa?status=pending",
                    },
                    "auto_return": "approved",
                    "metadata": {
                        "user_id": str(current_user.id),
                        "plan_id": plan["id"],
                        "business_id": str(payload.business_id) if payload.business_id else None,
                    },
                    "notification_url": f"{app_url}/api/v1/payments/mercadopago/webhook",
                }
                res = await client.post(
                    "https://api.mercadopago.com/checkout/preferences",
                    headers={
                        "Authorization": f"Bearer {mp_token}",
                        "Content-Type": "application/json",
                    },
                    json=mp_payload,
                )
                if res.status_code in (200, 201):
                    mp_data = res.json()
                    init_point = mp_data.get("init_point")
                    return {
                        "success": True,
                        "preference_id": mp_data.get("id"),
                        "init_point": init_point,
                        "plan": plan,
                        "is_live": True,
                    }
        except Exception as e:
            logger.error("Erro ao comunicar com Mercado Pago: %s", e)

    # Modo Sandbox / Simulação caso o token do Mercado Pago não esteja preenchido
    mock_pref_id = f"pref_{secrets.token_hex(8)}"
    return {
        "success": True,
        "preference_id": mock_pref_id,
        "init_point": f"/painel-empresa?checkout=simulated&plan={plan['id']}&pref={mock_pref_id}",
        "plan": plan,
        "is_live": False,
        "message": "Preferência gerada em modo simulação. Configure MERCADO_PAGO_ACCESS_TOKEN no .env para pagamentos em produção.",
    }


async def activate_user_subscription(
    db: AsyncSession,
    user_id: UUID,
    plan_id: str,
    payment_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    T4.2 & T4.5: Ativa ou prorroga a assinatura e bonifica o indicador apenas se:
    1. Não for auto-indicação
    2. Não houver duplicidade de CPF/CNPJ ou telefone
    3. A empresa indicada estiver APROVADA pela moderação
    4. O indicador não tiver excedido o limite de 12 meses bônus
    """
    # 1. Obter duração oficial do plano no banco de dados
    duration_months = 12
    plan_name = "Plano Anual"
    try:
        p_stmt = select(Plan).where(Plan.id == plan_id)
        plan_record = (await db.execute(p_stmt)).scalars().first()
        if plan_record:
            duration_months = plan_record.duration_months
            plan_name = plan_record.name
    except Exception:
        fallback = next((p for p in DEFAULT_PLANS_SEED if p["id"] == plan_id), None)
        if fallback:
            duration_months = fallback["duration_months"]
            plan_name = fallback["name"]

    days = duration_months * 30
    now = datetime.now(timezone.utc)
    new_end = now + timedelta(days=days)

    # 2. Ativar ou prorrogar assinatura do usuário
    sub_stmt = select(Subscription).where(Subscription.owner_user_id == user_id)
    sub = (await db.execute(sub_stmt)).scalars().first()

    if sub:
        if sub.current_period_end > now and sub.status in ("active", "grace_period"):
            sub.current_period_end += timedelta(days=days)
        else:
            sub.current_period_end = new_end
        sub.status = "active"
        sub.plan_id = plan_id
        if payment_id:
            sub.mp_payment_id = payment_id
    else:
        sub = Subscription(
            owner_user_id=user_id,
            plan_id=plan_id,
            status="active",
            current_period_start=now,
            current_period_end=new_end,
            mp_payment_id=payment_id or f"pay_sim_{secrets.token_hex(4)}",
        )
        db.add(sub)

    await db.flush()

    # 3. T4.5: Tratamento rigoroso de indicação com anti-fraude
    rewarded_referrer = None
    ref_stmt = select(Referral).where(
        Referral.referred_user_id == user_id,
        Referral.status == "pending",
    )
    referral = (await db.execute(ref_stmt)).scalars().first()

    if referral and referral.referrer_user_id:
        if referral.referrer_user_id == user_id:
            referral.status = "fraud_blocked"
            logger.warning("Bloqueio de auto-indicação: referrer_user_id == referred_user_id (%s)", user_id)
        else:
            # Checar documentos e telefones compartilhados
            referrer_bizs = (await db.execute(select(Business).where(Business.owner_user_id == referral.referrer_user_id))).scalars().all()
            referred_bizs = (await db.execute(select(Business).where(Business.owner_user_id == user_id))).scalars().all()

            ref_docs = {b.document_number for b in referrer_bizs if b.document_number}
            referred_docs = {b.document_number for b in referred_bizs if b.document_number}

            ref_phones = {b.whatsapp_e164 or b.whatsapp for b in referrer_bizs if b.whatsapp}
            referred_phones = {b.whatsapp_e164 or b.whatsapp for b in referred_bizs if b.whatsapp}

            is_duplicate = bool(ref_docs.intersection(referred_docs)) or bool(ref_phones.intersection(referred_phones))

            # Verificar se a empresa indicada está aprovada
            target_biz = (await db.execute(select(Business).where(Business.id == referral.referred_business_id))).scalars().first()
            is_approved = target_biz and target_biz.status == "approved"

            if is_duplicate:
                referral.status = "fraud_blocked"
                logger.warning("Bloqueio de auto-indicação por documento/telefone entre referrer %s e referred %s", referral.referrer_user_id, user_id)
            elif not is_approved:
                logger.info("Indicação mantida pendente: empresa %s ainda aguarda aprovação da moderação", referral.referred_business_id)
            else:
                referrer_sub = (await db.execute(select(Subscription).where(Subscription.owner_user_id == referral.referrer_user_id))).scalars().first()
                if referrer_sub:
                    if referrer_sub.bonus_months_applied < 12:
                        referrer_sub.current_period_end += timedelta(days=30)
                        referrer_sub.bonus_months_applied += 1
                        referral.status = "rewarded"
                        referral.rewarded_at = now
                        rewarded_referrer = str(referral.referrer_user_id)
                        logger.info("Bônus de 30 dias concedido ao indicador %s", referral.referrer_user_id)
                    else:
                        logger.info("Limite de 12 meses bônus já atingido pelo indicador %s", referral.referrer_user_id)

    await db.commit()

    return {
        "success": True,
        "message": f"Assinatura do {plan_name} ativada com sucesso até {sub.current_period_end.strftime('%d/%m/%Y')}!",
        "current_period_end": sub.current_period_end.isoformat(),
        "rewarded_referrer_user_id": rewarded_referrer,
    }


async def cancel_user_subscription(
    db: AsyncSession,
    user_id: UUID,
    payment_id: Optional[str] = None,
) -> None:
    """
    T4.3: Revoga os benefícios da assinatura em caso de estorno ou reembolso.
    """
    sub_stmt = select(Subscription).where(Subscription.owner_user_id == user_id)
    sub = (await db.execute(sub_stmt)).scalars().first()
    if sub:
        sub.status = "canceled"
        sub.current_period_end = datetime.now(timezone.utc)
        await db.commit()
        logger.info("Assinatura do usuário %s cancelada por estorno/reembolso no pagamento %s", user_id, payment_id)


@router.post("/mercadopago/webhook")
async def mercadopago_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    T4.3: Webhook endurecido do Mercado Pago com:
    1. Validação estrita de cabeçalho x-signature (HMAC-SHA256)
    2. Validação de moeda (BRL) e conferência de preço (anti-fraude)
    3. Idempotência transacional via tabela 'payments' (evita múltiplas prorrogações)
    4. Tratamento de estorno/reembolso cancelando benefícios
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    topic = body.get("type") or body.get("topic") or request.query_params.get("topic") or request.query_params.get("type")
    data_id = (body.get("data") or {}).get("id") or body.get("id") or request.query_params.get("id") or request.query_params.get("data.id")

    # 1. T4.3: Validar x-signature (HMAC-SHA256)
    x_signature = request.headers.get("x-signature")
    x_request_id = request.headers.get("x-request-id")
    secret = settings.MERCADO_PAGO_WEBHOOK_SECRET

    if secret:
        is_valid = verify_mercadopago_signature(
            x_signature=x_signature,
            x_request_id=x_request_id,
            data_id=str(data_id) if data_id else "",
            secret=secret,
        )
        if not is_valid:
            logger.warning("Tentativa de webhook forjado rejeitada (HMAC inválido): data_id=%s", data_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Assinatura do webhook inválida.",
            )

    logger.info("Webhook Mercado Pago recebido e validado: topic=%s id=%s", topic, data_id)

    if (str(topic) in ("payment", "payment.updated", "payment.created") or str(topic).startswith("payment")) and data_id:
        mp_token = settings.MERCADO_PAGO_ACCESS_TOKEN
        if mp_token:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.get(
                        f"https://api.mercadopago.com/v1/payments/{data_id}",
                        headers={"Authorization": f"Bearer {mp_token}"},
                    )
                    if res.status_code == 200:
                        payment_data = res.json()
                        payment_status = payment_data.get("status")  # 'approved', 'refunded', 'charged_back', etc.
                        currency = payment_data.get("currency_id", "BRL")
                        transaction_amount = payment_data.get("transaction_amount")
                        metadata = payment_data.get("metadata", {})
                        user_id_str = metadata.get("user_id")
                        plan_id = metadata.get("plan_id", "anual")
                        business_id_str = metadata.get("business_id")

                        # Validação de Moeda
                        if currency and currency != "BRL":
                            logger.error("Pagamento MP %s rejeitado: moeda %s inválida", data_id, currency)
                            return {"status": "rejected", "reason": "invalid_currency"}

                        # Validação de Preço (Anti-Fraude de adulteração de valor)
                        amount_cents = int(round(float(transaction_amount) * 100)) if transaction_amount is not None else 0
                        plan_stmt = select(Plan).where(Plan.id == plan_id)
                        plan_record = (await db.execute(plan_stmt)).scalars().first()
                        if plan_record and plan_record.price_cents != amount_cents:
                            logger.error(
                                "Pagamento MP %s rejeitado por divergência de valor: esperado %s centavos, recebido %s",
                                data_id,
                                plan_record.price_cents,
                                amount_cents,
                            )
                            return {"status": "rejected", "reason": "price_tampered"}

                        if user_id_str:
                            user_uuid = UUID(user_id_str)
                            biz_uuid = UUID(business_id_str) if business_id_str else None

                            # 3. T4.3: Idempotência transacional com tabela payments
                            inserted_id = None
                            try:
                                ins_stmt = (
                                    pg_insert(Payment)
                                    .values(
                                        mp_payment_id=str(data_id),
                                        user_id=user_uuid,
                                        business_id=biz_uuid,
                                        plan_id=plan_id,
                                        amount_cents=amount_cents,
                                        currency=currency,
                                        status=payment_status,
                                        raw_payload=payment_data,
                                    )
                                    .on_conflict_do_nothing(index_elements=["mp_payment_id"])
                                    .returning(Payment.id)
                                )
                                ins_res = await db.execute(ins_stmt)
                                row = ins_res.fetchone()
                                inserted_id = row[0] if row else None
                            except Exception:
                                # Fallback para compatibilidade em motores de teste
                                existing = (await db.execute(select(Payment).where(Payment.mp_payment_id == str(data_id)))).scalars().first()
                                if existing:
                                    inserted_id = None
                                else:
                                    p_row = Payment(
                                        mp_payment_id=str(data_id),
                                        user_id=user_uuid,
                                        business_id=biz_uuid,
                                        plan_id=plan_id,
                                        amount_cents=amount_cents,
                                        currency=currency,
                                        status=payment_status,
                                        raw_payload=payment_data,
                                    )
                                    db.add(p_row)
                                    await db.flush()
                                    inserted_id = p_row.id

                            if not inserted_id:
                                # Pagamento já havia sido processado anteriormente
                                if payment_status in ("refunded", "charged_back", "cancelled"):
                                    await cancel_user_subscription(db=db, user_id=user_uuid, payment_id=str(data_id))
                                    return {"status": "refund_processed"}

                                logger.info("Pagamento %s já processado. Idempotência garantida.", data_id)
                                return {"status": "already_processed"}

                            # Primeira vez processando este pagamento
                            if payment_status == "approved":
                                await activate_user_subscription(
                                    db=db,
                                    user_id=user_uuid,
                                    plan_id=plan_id,
                                    payment_id=str(data_id),
                                )
                                logger.info("Assinatura ativada via Webhook MP para o usuário %s no plano %s.", user_uuid, plan_id)
                            elif payment_status in ("refunded", "charged_back", "cancelled"):
                                await cancel_user_subscription(db=db, user_id=user_uuid, payment_id=str(data_id))
            except HTTPException:
                raise
            except Exception as e:
                logger.error("Erro ao consultar pagamento no webhook MP: %s", e)

    return {"status": "received"}


async def expire_overdue_subscriptions(db: AsyncSession) -> int:
    """
    T4.2: Rotina de expiração de assinaturas vencidas que ultrapassaram os 3 dias de carência.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=3)

    stmt = (
        update(Subscription)
        .where(
            Subscription.current_period_end < cutoff,
            Subscription.status.in_(["active", "grace_period"]),
        )
        .values(status="expired")
    )
    result = await db.execute(stmt)
    await db.commit()
    count = result.rowcount or 0
    if count > 0:
        logger.info("Job de expiração: %d assinaturas marcadas como 'expired'.", count)
    return count
