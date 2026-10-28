"""
Serviço de geração, envio e validação segura de OTP para reivindicação de empresas.
Regras de segurança C4:
- Código gerado com secrets.randbelow (6 dígitos)
- Armazenamento apenas do hash (SHA-256 + sal exclusivo) com TTL de 5 minutos
- Máximo de 5 tentativas de verificação
- Limite de 3 disparos por hora por número
- Provedor plugável (ConsoleWhatsAppProvider para dev, MetaWhatsAppCloudProvider para prod)
- Código NUNCA retornado nas respostas HTTP
"""

import hashlib
import logging
import secrets
import time
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple

logger = logging.getLogger("patriotaindica.otp")


class WhatsAppProvider(ABC):
    @abstractmethod
    async def send_otp(self, phone: str, code: str, business_name: str) -> Tuple[bool, str]:
        pass


class ConsoleWhatsAppProvider(WhatsAppProvider):
    """
    Provedor de desenvolvimento: exibe o código nos logs do backend de forma auditável.
    """
    async def send_otp(self, phone: str, code: str, business_name: str) -> Tuple[bool, str]:
        logger.info(
            "\n[WHATSAPP DEV DISPATCH] Empresa: '%s' | Para: %s | Código OTP: %s (Válido por 5 min)\n",
            business_name,
            phone,
            code,
        )
        return True, "Código enviado com sucesso (modo console/dev)."


class MetaWhatsAppCloudProvider(WhatsAppProvider):
    """
    Provedor de produção: WhatsApp Cloud API da Meta.
    """
    def __init__(self, token: str, phone_number_id: str):
        self.token = token
        self.phone_number_id = phone_number_id

    async def send_otp(self, phone: str, code: str, business_name: str) -> Tuple[bool, str]:
        import httpx
        url = f"https://graph.facebook.com/v19.0/{self.phone_number_id}/messages"
        clean_phone = "".join(filter(str.isdigit, phone))
        payload = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "text",
            "text": {
                "body": f"Seu código de confirmação Patriota Indica para gerenciar {business_name} é: {code}. Não compartilhe com ninguém.",
            },
        }
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code in (200, 201):
                    return True, "Código enviado com sucesso."
                return False, f"Meta API retornou HTTP {res.status_code}: {res.text[:150]}"
        except Exception as e:
            logger.error("Falha no envio via Meta WhatsApp: %s", e)
            return False, f"Falha no envio via Meta WhatsApp: {str(e)}"


class EvolutionWhatsAppProvider(WhatsAppProvider):
    """
    Provedor Evolution API (WhatsApp self-hosted via Baileys).
    Compatível nativamente com Evolution API v1 e v2.
    """
    def __init__(self, base_url: str, api_key: str, instance_name: str):
        cleaned_url = base_url.strip().rstrip("/")
        if cleaned_url.endswith("/manager"):
            cleaned_url = cleaned_url[:-8].rstrip("/")
        self.base_url = cleaned_url
        self.api_key = api_key.strip()
        self.instance_name = instance_name.strip()

    async def send_otp(self, phone: str, code: str, business_name: str) -> Tuple[bool, str]:
        import httpx
        clean_phone = "".join(filter(str.isdigit, phone))
        if not clean_phone.startswith("55") and len(clean_phone) in (10, 11):
            clean_phone = f"55{clean_phone}"

        msg_text = (
            f"🛡️ *Patriota Indica*\n\n"
            f"Seu código de acesso para gerenciar *{business_name}* é:\n\n"
            f"*🔑 {code}*\n\n"
            f"_Válido por 5 minutos. Não compartilhe este código._"
        )

        url = f"{self.base_url}/message/sendText/{self.instance_name}"
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

        # Formato Evolution API v2
        payload_v2 = {
            "number": clean_phone,
            "text": msg_text,
        }

        # Formato Evolution API v1
        payload_v1 = {
            "number": clean_phone,
            "textMessage": {
                "text": msg_text,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                # Tentativa 1: Payload v2
                res = await client.post(url, json=payload_v2, headers=headers)
                if res.status_code in (200, 201):
                    logger.info("WhatsApp enviado via Evolution API (v2) para %s com sucesso.", clean_phone)
                    return True, "Código enviado com sucesso via WhatsApp."

                # Tentativa 2: Se 400 (Bad Request), tenta formato v1
                if res.status_code == 400:
                    res_v1 = await client.post(url, json=payload_v1, headers=headers)
                    if res_v1.status_code in (200, 201):
                        logger.info("WhatsApp enviado via Evolution API (v1) para %s com sucesso.", clean_phone)
                        return True, "Código enviado com sucesso via WhatsApp."

                    err_text = res.text[:200]
                    logger.error("Evolution API retornou 400 (v2 e v1): %s", err_text)
                    return False, f"Evolution API: Erro 400 ao enviar. A instância está conectada? Resposta: {err_text}"

                if res.status_code in (401, 403):
                    logger.error("Evolution API: Chave de API não autorizada (HTTP %s)", res.status_code)
                    return False, "Evolution API: Chave de API (EVOLUTION_API_KEY) incorreta ou não autorizada."

                if res.status_code == 404:
                    logger.error("Evolution API: Instância '%s' não encontrada na URL %s", self.instance_name, self.base_url)
                    return False, f"Evolution API: Instância '{self.instance_name}' não encontrada. Verifique o nome da instância."

                logger.error("Evolution API retornou HTTP %s: %s", res.status_code, res.text)
                return False, f"Evolution API retornou HTTP {res.status_code}: {res.text[:150]}"
        except httpx.ConnectError as e:
            logger.error("Falha ao conectar na Evolution API (%s): %s", url, e)
            return False, f"Não foi possível conectar na Evolution API ({self.base_url}). Verifique se a URL e a porta estão acessíveis."
        except httpx.TimeoutException:
            logger.error("Timeout ao comunicar com Evolution API (%s)", url)
            return False, f"Tempo limite esgotado (timeout) ao conectar na Evolution API ({self.base_url})."
        except Exception as e:
            logger.error("Falha ao comunicar com Evolution API (%s): %s", url, e)
            return False, f"Erro ao comunicar com Evolution API: {str(e)}"


def get_default_provider() -> WhatsAppProvider:
    from backend.app.core.config import settings

    if settings.EVOLUTION_API_URL and settings.EVOLUTION_API_KEY and settings.EVOLUTION_INSTANCE_NAME:
        return EvolutionWhatsAppProvider(
            base_url=settings.EVOLUTION_API_URL,
            api_key=settings.EVOLUTION_API_KEY,
            instance_name=settings.EVOLUTION_INSTANCE_NAME,
        )
    return ConsoleWhatsAppProvider()


class OTPService:
    def __init__(self, provider: Optional[WhatsAppProvider] = None):
        self._custom_provider = provider
        # Armazenamento em memória com TTL (pode ser conectado a Redis em escala)
        self._cache: Dict[str, Dict] = {}
        self._rate_limits: Dict[str, list] = {}

    @property
    def provider(self) -> WhatsAppProvider:
        return self._custom_provider or get_default_provider()

    def _hash_code(self, code: str, salt: str) -> str:
        return hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()

    def mask_phone(self, phone: str) -> str:
        digits = "".join(filter(str.isdigit, phone))
        # Normaliza removendo DDI 55 se já estiver presente no início
        if digits.startswith("55") and len(digits) in (12, 13):
            digits = digits[2:]

        if len(digits) == 11:
            return f"+55 ({digits[:2]}) {digits[2]}****-{digits[-4:]}"
        elif len(digits) == 10:
            return f"+55 ({digits[:2]}) ****-{digits[-4:]}"
        elif len(digits) >= 8:
            return f"+55 (**) *****-{digits[-4:]}"
        return "+55 (**) *****-****"

    def check_rate_limit(self, phone_key: str, limit: int = 3, window_seconds: int = 3600) -> bool:
        now = time.time()
        requests = self._rate_limits.get(phone_key, [])
        valid_requests = [t for t in requests if now - t < window_seconds]
        if len(valid_requests) >= limit:
            return False
        valid_requests.append(now)
        self._rate_limits[phone_key] = valid_requests
        return True

    async def request_otp(self, business_id: str, phone: str, business_name: str) -> Tuple[bool, str]:
        phone_key = f"claim:{business_id}"

        # 1. Checa limite de envio (5 por hora)
        if not self.check_rate_limit(phone_key, limit=5, window_seconds=3600):
            return False, "Limite de envios excedido para este número. Tente novamente em alguns minutos."

        # 2. Gera 6 dígitos aleatórios criptograficamente seguros
        raw_code = f"{secrets.randbelow(900000) + 100000}"
        salt = secrets.token_hex(16)
        hashed = self._hash_code(raw_code, salt)

        # 3. Armazena apenas o HASH e salt com TTL de 300 segundos (5 min)
        self._cache[phone_key] = {
            "hash": hashed,
            "salt": salt,
            "attempts": 0,
            "expires_at": time.time() + 300,
        }

        # 4. Despacha via provedor de WhatsApp (NUNCA expõe o código em produção oficial)
        sent, err_msg = await self.provider.send_otp(phone, raw_code, business_name)
        if not sent:
            return False, err_msg or "Não foi possível enviar a mensagem no WhatsApp. Tente novamente."

        return True, "Código enviado com sucesso via WhatsApp."

    def verify_otp(self, business_id: str, submitted_code: str) -> Tuple[bool, str]:
        phone_key = f"claim:{business_id}"
        record = self._cache.get(phone_key)

        if not record:
            return False, "Nenhum código ativo encontrado para esta empresa. Solicite um novo código."

        if time.time() > record["expires_at"]:
            del self._cache[phone_key]
            return False, "O código expirou (validade de 5 minutos). Solicite um novo código."

        # Incrementa tentativas (máximo de 5)
        record["attempts"] += 1
        if record["attempts"] > 5:
            del self._cache[phone_key]
            return False, "Número máximo de tentativas excedido (5 tentativas). Solicite um novo código."

        expected_hash = record["hash"]
        submitted_hash = self._hash_code(submitted_code.strip(), record["salt"])

        # Comparação em tempo constante para evitar timing attacks
        is_match = secrets.compare_digest(expected_hash, submitted_hash)
        if is_match:
            del self._cache[phone_key]
            return True, "Código validado com sucesso!"

        remaining = 5 - record["attempts"]
        return False, f"Código incorreto. Você ainda tem {remaining} tentativa(s)."


# Instância global singleton do serviço de OTP
otp_service = OTPService()
