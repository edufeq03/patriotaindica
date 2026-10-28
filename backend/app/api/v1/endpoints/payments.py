import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.business import Business
from backend.app.models.subscription import Plan, Referral, Subscription
from backend.app.models.user import User

logger = logging.getLogger("patriotaindica.payments")
router = APIRouter()

PLANS_METADATA = {
    "mensal": {
        "id": "mensal",
        "name": "Plano Mensal",
        "price_cents": 1500,
        "price_formatted": "R$ 15,00",
        "monthly_equivalent": "R$ 15,00",
        "duration_months": 1,
        "description": "Flexibilidade total, sem fidelidade. Cancele quando quiser.",
        "badge": "Sem Fidelidade",
        "popular": False,
    },
    "semestral": {
        "id": "semestral",
        "name": "Plano Semestral",
        "price_cents": 7794,
        "price_formatted": "R$ 77,94",
        "monthly_equivalent": "R$ 12,99",
        "duration_months": 6,
        "description": "6 meses garantidos de visibilidade na sua região com 13% de economia.",
        "badge": "Economize 13%",
        "popular": False,
    },
    "anual": {
        "id": "anual",
        "name": "Plano Anual",
        "price_cents": 11988,
        "price_formatted": "R$ 119,88",
        "monthly_equivalent": "R$ 9,99",
        "duration_months": 12,
        "description": "O mais escolhido pelos empresários patriotas: menos de R$ 0,33 por dia (em até 12x de R$ 9,99).",
        "badge": "Mais Popular • 33% OFF",
        "popular": True,
    },
}


class CreatePreferenceRequest(BaseModel):
    plan_id: str = Field(..., pattern="^(mensal|semestral|anual)$")
    business_id: Optional[UUID] = None


@router.get("/plans")
async def get_plans(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Retorna os 3 planos oficiais para exibição na Home e no Painel da Empresa.
    """
    return list(PLANS_METADATA.values())


@router.get("/my-subscription")
async def get_my_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Consulta o status da assinatura do proprietário autenticado.
    Fase 1: Assinatura da conta cobre todos os negócios aprovados da dona.
    """
    # 1. Buscar assinatura ativa mais recente
    stmt = (
        select(Subscription)
        .where(Subscription.owner_user_id == current_user.id)
        .order_by(Subscription.current_period_end.desc())
    )
    sub = (await db.execute(stmt)).scalars().first()

    now = datetime.now(timezone.utc)
    is_active = sub is not None and sub.current_period_end > now and sub.status == "active"
    days_remaining = max(0, (sub.current_period_end - now).days) if (sub and is_active) else 0

    # 2. Buscar empresas do dono para obter o código de indicação
    biz_stmt = select(Business).where(Business.owner_user_id == current_user.id)
    businesses = (await db.execute(biz_stmt)).scalars().all()

    primary_biz = businesses[0] if businesses else None
    referral_code = primary_biz.referral_code if primary_biz else f"PAT-{str(current_user.id)[:6].upper()}"

    # 3. Estatísticas do programa Indique e Ganhe (+30 dias por amigo)
    ref_count_stmt = select(func.count(Referral.id)).where(Referral.referrer_user_id == current_user.id)
    total_referred = (await db.execute(ref_count_stmt)).scalar() or 0

    rewarded_count_stmt = select(func.count(Referral.id)).where(
        Referral.referrer_user_id == current_user.id,
        Referral.status == "rewarded"
    )
    total_rewarded = (await db.execute(rewarded_count_stmt)).scalar() or 0

    return {
        "has_subscription": sub is not None,
        "is_active": is_active,
        "status": sub.status if sub else "none",
        "plan_id": sub.plan_id if sub else None,
        "plan_name": PLANS_METADATA.get(sub.plan_id, {}).get("name") if sub else None,
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Gera link de checkout do Mercado Pago para pagamento via Pix ou Cartão em até 12x.
    """
    plan = PLANS_METADATA.get(payload.plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail="Plano inválido.")

    # Se Mercado Pago tiver token de produção/teste configurado
    mp_token = settings.MERCADO_PAGO_ACCESS_TOKEN
    unit_price = float(plan["price_cents"]) / 100.0

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
                        "success": f"{settings.CORS_ORIGINS[0]}/painel-empresa?status=success",
                        "failure": f"{settings.CORS_ORIGINS[0]}/painel-empresa?status=failure",
                        "pending": f"{settings.CORS_ORIGINS[0]}/painel-empresa?status=pending",
                    },
                    "auto_return": "approved",
                    "metadata": {
                        "user_id": str(current_user.id),
                        "plan_id": plan["id"],
                        "business_id": str(payload.business_id) if payload.business_id else None,
                    },
                    "notification_url": f"{settings.CORS_ORIGINS[0]}/api/v1/payments/mercadopago/webhook",
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
            logger.error(f"Erro ao comunicar com Mercado Pago: {e}")

    # Modo Sandbox / Simulação caso o token do Mercado Pago ainda não esteja preenchido no .env
    mock_pref_id = f"pref_{secrets.token_hex(8)}"
    return {
        "success": True,
        "preference_id": mock_pref_id,
        "init_point": f"/painel-empresa?checkout=simulated&plan={plan['id']}&pref={mock_pref_id}",
        "plan": plan,
        "is_live": False,
        "message": "Preferência gerada. Configure MERCADO_PAGO_ACCESS_TOKEN no .env para pagamentos reais com Pix/Cartão.",
    }


async def activate_user_subscription(
    db: AsyncSession,
    user_id: UUID,
    plan_id: str,
    payment_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Função centralizada para ativar ou prorrogar assinatura de um usuário
    e bonificar o indicador com +30 dias grátis caso aplicável.
    """
    plan = PLANS_METADATA.get(plan_id, PLANS_METADATA["anual"])
    days = plan["duration_months"] * 30

    now = datetime.now(timezone.utc)
    new_end = now + timedelta(days=days)

    # 1. Ativar ou estender assinatura
    sub_stmt = select(Subscription).where(Subscription.owner_user_id == user_id)
    sub = (await db.execute(sub_stmt)).scalars().first()

    if sub:
        if sub.current_period_end > now:
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

    # 2. Verificar se o usuário foi indicado por outra empresa e conceder +30 dias para o indicador
    rewarded_referrer = None
    ref_stmt = select(Referral).where(
        Referral.referred_user_id == user_id,
        Referral.status == "pending"
    )
    referral = (await db.execute(ref_stmt)).scalars().first()

    if referral and referral.referrer_user_id:
        referrer_sub_stmt = select(Subscription).where(Subscription.owner_user_id == referral.referrer_user_id)
        referrer_sub = (await db.execute(referrer_sub_stmt)).scalars().first()
        if referrer_sub:
            referrer_sub.current_period_end += timedelta(days=30)
            referrer_sub.bonus_months_applied += 1
            referral.status = "rewarded"
            referral.rewarded_at = now
            rewarded_referrer = str(referral.referrer_user_id)

    await db.commit()

    return {
        "success": True,
        "message": f"Assinatura do {plan['name']} ativada com sucesso até {sub.current_period_end.strftime('%d/%m/%Y')}!",
        "current_period_end": sub.current_period_end.isoformat(),
        "rewarded_referrer_user_id": rewarded_referrer,
    }


@router.post("/mercadopago/webhook")
async def mercadopago_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Webhook que recebe aprovação de pagamento do Mercado Pago (Pix ou Cartão).
    - Consulta o status oficial do pagamento na API do Mercado Pago
    - Ativa a assinatura do proprietário
    - Bonifica o indicador com +30 dias grátis se veio de indicação
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    topic = body.get("type") or body.get("topic")
    data_id = (body.get("data") or {}).get("id") or body.get("id")

    logger.info("Webhook Mercado Pago recebido: topic=%s id=%s", topic, data_id)

    if (topic in ("payment", "payment.updated", "payment.created") or str(topic).startswith("payment")) and data_id:
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
                        if payment_data.get("status") == "approved":
                            metadata = payment_data.get("metadata", {})
                            user_id_str = metadata.get("user_id")
                            plan_id = metadata.get("plan_id", "anual")
                            if user_id_str:
                                user_uuid = UUID(user_id_str)
                                await activate_user_subscription(
                                    db=db,
                                    user_id=user_uuid,
                                    plan_id=plan_id,
                                    payment_id=str(data_id),
                                )
                                logger.info("Assinatura ativada via Webhook MP para o usuário %s no plano %s.", user_uuid, plan_id)
            except Exception as e:
                logger.error("Erro ao consultar pagamento no webhook MP: %s", e)

    return {"status": "received"}


@router.post("/simulate-activation")
async def simulate_activation(
    plan_id: str = Query(..., pattern="^(mensal|semestral|anual)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Endpoint de teste / homologação para simular ativação e testar a bonificação de 1 mês grátis.
    """
    return await activate_user_subscription(
        db=db,
        user_id=current_user.id,
        plan_id=plan_id,
    )
