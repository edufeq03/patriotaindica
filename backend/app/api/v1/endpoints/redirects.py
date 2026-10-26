import ipaddress
import re
import urllib.parse
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.models.business import Business
from backend.app.models.events import ContactEvent

router = APIRouter()

BOT_USER_AGENT_PATTERN = re.compile(
    r"(bot|crawler|spider|facebookexternalhit|whatsapp|telegrambot|slackbot|discordbot|twitterbot|meta-externalagent)",
    re.IGNORECASE,
)


def validate_external_url(url_str: str) -> str:
    """
    SEGURANÇA (H5): Validação rígida de URL de redirecionamento para evitar
    ataques de Phishing, SSRF, e Open Redirect para IPs privados.
    """
    if "://" in url_str:
        if not url_str.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Esquema de URL não permitido.")
    else:
        url_str = f"https://{url_str}"

    try:
        parsed = urllib.parse.urlparse(url_str)
    except Exception:
        raise HTTPException(status_code=400, detail="URL malformatada.")

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Esquema de URL não permitido.")

    # Rejeitar credenciais na URL (ex: user:pass@host)
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="Credenciais em URL não são permitidas.")

    host = parsed.hostname
    if not host:
        raise HTTPException(status_code=400, detail="Host inválido na URL.")

    # Rejeitar localhost e portas de serviços internos
    if host.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        raise HTTPException(status_code=400, detail="Destino de redirecionamento não permitido.")

    # Rejeitar portas não-padrão (evitar port scanning ou serviços internos)
    if parsed.port and parsed.port not in (80, 443, 8080):
        raise HTTPException(status_code=400, detail="Porta não permitida.")

    # Rejeitar faixas de IP privado / local
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            raise HTTPException(status_code=400, detail="Endereço de rede interna não permitido.")
    except ValueError:
        # É um domínio regular (ex: www.exemplo.com.br), tudo certo
        pass

    return url_str


@router.get("/{event_type}/{business_id}")
async def redirect_contact_event(
    event_type: str,
    business_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_agent: str = Header(None),
    referer: str = Header(None),
):
    """
    Rastreamento de métricas e conversão de cliques:
    SEGURANÇA:
    - [H1] Rate limit por IP (30/min).
    - [H5] Sanitização e bloqueio de SSRF/phishing em website.
    - [M5] Detecção de bots, descarte de prefetch, deduplicação de cliques repetidos e truncamento.
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:redirect:{client_ip}",
        limit=30,
        window_seconds=60,
        error_msg="Muitas requisições de redirecionamento em curto intervalo.",
    )

    if event_type not in ("whatsapp", "phone", "website"):
        raise HTTPException(status_code=400, detail="Tipo de contato inválido.")

    # Buscar empresa aprovada
    stmt = select(Business).where(
        Business.id == business_id,
        Business.status == "approved",
    )
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(status_code=404, detail="Empresa não encontrada ou não ativa.")

    # Verificar se é requisição de prefetch de navegador (M5)
    purpose = request.headers.get("Purpose", "") or request.headers.get("Sec-Purpose", "")
    is_prefetch = "prefetch" in purpose.lower()

    # Detectar robôs de pré-visualização (WhatsApp/Facebook preview bots)
    ua_str = user_agent or ""
    is_bot = bool(BOT_USER_AGENT_PATTERN.search(ua_str))

    # Gravar métrica em contact_events apenas para cliques humanos reais
    if not is_prefetch and not is_bot:
        try:
            # Deduplicação: até 1 clique por tipo/empresa a cada 60s do mesmo IP
            await check_rate_limit(
                key=f"dedup_click:{client_ip}:{business_id}:{event_type}",
                limit=1,
                window_seconds=60,
            )
            event = ContactEvent(
                business_id=business.id,
                event_type=event_type,
                city=business.city,
                referrer=referer[:255] if referer else None,
                user_agent=ua_str[:255] if ua_str else None,
            )
            db.add(event)
            await db.commit()
        except HTTPException:
            # Clique repetido deduplicado: não grava no banco, apenas redireciona
            pass

    # 2. Construir destino do redirecionamento
    destination_url = ""
    if event_type == "whatsapp":
        clean_number = "".join(filter(str.isdigit, business.whatsapp))
        if not clean_number.startswith("55") and len(clean_number) in (10, 11):
            clean_number = f"55{clean_number}"

        default_msg = f"Olá! Vi seu anúncio no Patriota Indica e gostaria de solicitar informações/orçamento sobre {business.name}."
        encoded_msg = urllib.parse.quote(default_msg)
        destination_url = f"https://wa.me/{clean_number}?text={encoded_msg}"

    elif event_type == "phone":
        clean_phone = "".join(filter(str.isdigit, business.phone or business.whatsapp))
        destination_url = f"tel:{clean_phone}"

    elif event_type == "website":
        if not business.website:
            raise HTTPException(status_code=400, detail="Empresa não possui site cadastrado.")
        destination_url = validate_external_url(business.website)

    # Redirecionamento 307 com cabeçalho de proteção
    response = RedirectResponse(url=destination_url, status_code=307)
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
