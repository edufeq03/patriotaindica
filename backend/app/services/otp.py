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

    if (settings.WHATSAPP_PROVIDER or "").lower() == "meta_cloud" and settings.META_WHATSAPP_ACCESS_TOKEN and settings.META_WHATSAPP_PHONE_NUMBER_ID:
        return MetaWhatsAppCloudProvider(
            token=settings.META_WHATSAPP_ACCESS_TOKEN,
            phone_number_id=settings.META_WHATSAPP_PHONE_NUMBER_ID,
        )

    if settings.EVOLUTION_API_URL and settings.EVOLUTION_API_KEY and settings.EVOLUTION_INSTANCE_NAME:
        return EvolutionWhatsAppProvider(
            base_url=settings.EVOLUTION_API_URL,
            api_key=settings.EVOLUTION_API_KEY,
            instance_name=settings.EVOLUTION_INSTANCE_NAME,
        )
    return ConsoleWhatsAppProvider()



def normalize_e164(phone: str) -> Optional[str]:
    """
    Normaliza um número de telefone brasileiro para o padrão internacional E.164 (+55...).
    Exemplos:
      "19999998888"   -> "+5519999998888"
      "(19) 99999-8888" -> "+5519999998888"
      "5519999998888" -> "+5519999998888"
      "+5519999998888"-> "+5519999998888"
    """
    if not phone:
        return None
    digits = "".join(filter(str.isdigit, phone))
    if digits.startswith("55") and len(digits) in (12, 13):
        return f"+{digits}"
    if len(digits) in (10, 11):
        return f"+55{digits}"
    if phone.strip().startswith("+") and len(digits) >= 10:
        return f"+{digits}"
    return None


def hash_phone(phone_e164: str) -> str:
    """Retorna o hash SHA-256 do telefone normalizado para chaves de rate limit e cache."""
    return hashlib.sha256(phone_e164.strip().encode("utf-8")).hexdigest()


class OTPService:
    def __init__(self, provider: Optional[WhatsAppProvider] = None):
        self._custom_provider = provider
        # Armazenamento em memória com TTL
        self._cache: Dict[str, Dict] = {}
        self._rate_limits: Dict[str, list] = {}
        self._biz_phone_map: Dict[str, str] = {}

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

    def check_rate_limit(self, key: str, limit: int = 3, window_seconds: int = 3600) -> bool:
        now = time.time()
        requests = self._rate_limits.get(key, [])
        valid_requests = [t for t in requests if now - t < window_seconds]
        if len(valid_requests) >= limit:
            return False
        valid_requests.append(now)
        self._rate_limits[key] = valid_requests
        return True

    async def request_otp_by_e164(
        self,
        phone_e164: str,
        business_name: str = "Patriota Indica",
    ) -> Tuple[bool, str]:
        """
        Dispara OTP para um telefone E.164.
        SEGURANÇA (T1.1):
        - Limite de 3 envios por hora por telefone normalizado
        - 6 dígitos randômicos seguros (secrets.randbelow)
        - Armazena apenas hash + sal com TTL de 300 segundos
        """
        phone_h = hash_phone(phone_e164)
        rate_key = f"otp:rate:{phone_h}"

        if not self.check_rate_limit(rate_key, limit=3, window_seconds=3600):
            return False, "Limite de envios excedido para este número (máximo 3 por hora). Tente novamente mais tarde."

        raw_code = f"{secrets.randbelow(900000) + 100000}"
        salt = secrets.token_hex(16)
        hashed = self._hash_code(raw_code, salt)

        cache_key = f"otp:{phone_h}"
        self._cache[cache_key] = {
            "hash": hashed,
            "salt": salt,
            "attempts": 0,
            "expires_at": time.time() + 300,
        }

        sent, err_msg = await self.provider.send_otp(phone_e164, raw_code, business_name)
        if not sent:
            return False, err_msg or "Não foi possível enviar a mensagem no WhatsApp. Tente novamente."

        return True, "Código enviado com sucesso via WhatsApp."

    def verify_otp_by_e164(self, phone_e164: str, submitted_code: str) -> Tuple[bool, str]:
        """
        Valida o código OTP informado contra o telefone E.164.
        SEGURANÇA (T1.1):
        - Comparação em tempo constante (secrets.compare_digest)
        - Máximo de 5 tentativas por código gerado
        - Destrói o código no cache na 5ª falha para impedir brute force
        - Destrói o código imediatamente após validação com sucesso (uso único)
        """
        phone_h = hash_phone(phone_e164)
        cache_key = f"otp:{phone_h}"
        record = self._cache.get(cache_key)

        if not record:
            return False, "Nenhum código ativo encontrado para este número. Solicite um novo código."

        if time.time() > record["expires_at"]:
            del self._cache[cache_key]
            return False, "O código expirou (validade de 5 minutos). Solicite um novo código."

        record["attempts"] += 1
        if record["attempts"] > 5:
            del self._cache[cache_key]
            return False, "Número máximo de tentativas excedido (5 tentativas). Código bloqueado. Solicite um novo código."

        expected_hash = record["hash"]
        submitted_hash = self._hash_code(submitted_code.strip(), record["salt"])

        is_match = secrets.compare_digest(expected_hash, submitted_hash)
        if is_match:
            del self._cache[cache_key]
            return True, "Código validado com sucesso!"

        remaining = 5 - record["attempts"]
        if remaining <= 0:
            del self._cache[cache_key]
            return False, "Número máximo de tentativas excedido (5 tentativas). Código bloqueado. Solicite um novo código."

        return False, f"Código incorreto. Você ainda tem {remaining} tentativa(s)."

    async def request_otp(self, business_id: str, phone: str, business_name: str) -> Tuple[bool, str]:
        """Compatibilidade retroativa: delega para request_otp_by_e164 e mapeia business_id."""
        normalized = normalize_e164(phone) or phone
        self._biz_phone_map[str(business_id)] = normalized
        ok, msg = await self.request_otp_by_e164(normalized, business_name)
        if ok:
            phone_h = hash_phone(normalized)
            if f"otp:{phone_h}" in self._cache:
                self._cache[f"claim:{business_id}"] = self._cache[f"otp:{phone_h}"]
        return ok, msg

    def verify_otp(self, business_id: str, submitted_code: str) -> Tuple[bool, str]:
        """Compatibilidade retroativa: resolve o telefone do business_id e valida."""
        phone = self._biz_phone_map.get(str(business_id))
        claim_key = f"claim:{business_id}"
        if phone:
            res = self.verify_otp_by_e164(phone, submitted_code)
            phone_h = hash_phone(phone)
            if f"otp:{phone_h}" not in self._cache:
                self._cache.pop(claim_key, None)
            return res
        if claim_key in self._cache:
            record = self._cache[claim_key]
            record["attempts"] += 1
            if record["attempts"] > 5 or time.time() > record["expires_at"]:
                del self._cache[claim_key]
                return False, "Código expirado ou número máximo de tentativas excedido (5 tentativas)."
            expected_hash = record["hash"]
            submitted_hash = self._hash_code(submitted_code.strip(), record["salt"])
            if secrets.compare_digest(expected_hash, submitted_hash):
                del self._cache[claim_key]
                return True, "Código validado com sucesso!"
            remaining = 5 - record["attempts"]
            return False, f"Código incorreto. Você ainda tem {remaining} tentativa(s)."
        return False, "Nenhum código ativo encontrado para esta empresa. Solicite um novo código."


# Instância global singleton do serviço de OTP
otp_service = OTPService()
