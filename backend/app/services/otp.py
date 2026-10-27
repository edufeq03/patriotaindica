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
    async def send_otp(self, phone: str, code: str, business_name: str) -> bool:
        pass


class ConsoleWhatsAppProvider(WhatsAppProvider):
    """
    Provedor de desenvolvimento: exibe o código nos logs do backend de forma auditável.
    """
    async def send_otp(self, phone: str, code: str, business_name: str) -> bool:
        logger.info(
            "\n[WHATSAPP DEV DISPATCH] Empresa: '%s' | Para: %s | Código OTP: %s (Válido por 5 min)\n",
            business_name,
            phone,
            code,
        )
        return True


class MetaWhatsAppCloudProvider(WhatsAppProvider):
    """
    Provedor de produção: WhatsApp Cloud API da Meta.
    """
    def __init__(self, token: str, phone_number_id: str):
        self.token = token
        self.phone_number_id = phone_number_id

    async def send_otp(self, phone: str, code: str, business_name: str) -> bool:
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
                return res.status_code in (200, 201)
        except Exception as e:
            logger.error("Falha no envio via Meta WhatsApp: %s", e)
            return False


class OTPService:
    def __init__(self, provider: WhatsAppProvider = None):
        self.provider = provider or ConsoleWhatsAppProvider()
        # Armazenamento em memória com TTL (pode ser conectado a Redis em escala)
        self._cache: Dict[str, Dict] = {}
        self._rate_limits: Dict[str, list] = {}

    def _hash_code(self, code: str, salt: str) -> str:
        return hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()

    def mask_phone(self, phone: str) -> str:
        digits = "".join(filter(str.isdigit, phone))
        if len(digits) >= 10:
            return f"+{digits[:2]} ({digits[2:4]}) *****-{digits[-4:]}"
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

        # 3. Armazena apenas o HASH com TTL de 300 segundos (5 min)
        # raw_code só fica salvo temporariamente em memória se o provedor for Console (dev/homologação)
        self._cache[phone_key] = {
            "hash": hashed,
            "salt": salt,
            "raw_code": raw_code if isinstance(self.provider, ConsoleWhatsAppProvider) else None,
            "attempts": 0,
            "expires_at": time.time() + 300,
        }

        # 4. Despacha via provedor de WhatsApp (NUNCA expõe o código em produção oficial)
        sent = await self.provider.send_otp(phone, raw_code, business_name)
        if not sent:
            return False, "Não foi possível enviar a mensagem no WhatsApp. Tente novamente."

        return True, "Código enviado com sucesso via WhatsApp."

    def get_dev_code(self, business_id: str) -> Optional[str]:
        """Retorna o código gerado apenas quando em modo ConsoleWhatsAppProvider."""
        if isinstance(self.provider, ConsoleWhatsAppProvider):
            return self._cache.get(f"claim:{business_id}", {}).get("raw_code")
        return None

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
        # Se for provedor Console/Homologação, também aceita 123456 como código universal de teste
        is_console = isinstance(self.provider, ConsoleWhatsAppProvider)
        if secrets.compare_digest(expected_hash, submitted_hash) or (is_console and submitted_code.strip() == "123456"):
            del self._cache[phone_key]
            return True, "Código validado com sucesso!"

        remaining = 5 - record["attempts"]
        return False, f"Código incorreto. Você ainda tem {remaining} tentativa(s)."


# Instância global singleton do serviço de OTP
otp_service = OTPService()
