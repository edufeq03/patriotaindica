import logging
from typing import List, Optional, Tuple
import httpx

from backend.app.services.whatsapp.base import WhatsAppButton, WhatsAppProvider, clean_phone_number

logger = logging.getLogger("patriotaindica.whatsapp.meta")


class MetaCloudWhatsAppProvider(WhatsAppProvider):
    """
    Driver para a WhatsApp Cloud API Oficial da Meta (Graph API v19+).
    Garantia de 99.9% de uptime, sem risco de banimento e com suporte a templates oficiais.
    """

    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token.strip()
        self.phone_number_id = phone_number_id.strip()
        self.base_url = f"https://graph.facebook.com/v19.0/{self.phone_number_id}/messages"

    @property
    def provider_name(self) -> str:
        return "meta_cloud"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def send_text(self, to_phone: str, text: str) -> Tuple[bool, str]:
        clean_phone = clean_phone_number(to_phone)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "text",
            "text": {
                "preview_url": True,
                "body": text,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self.base_url, json=payload, headers=self._headers())
                if res.status_code in (200, 201):
                    logger.info("WhatsApp enviado via Meta Cloud API para %s com sucesso.", clean_phone)
                    return True, "Mensagem enviada com sucesso via Meta Cloud API."

                err_msg = f"Meta Cloud API retornou HTTP {res.status_code}: {res.text[:150]}"
                logger.error(err_msg)
                return False, err_msg
        except Exception as e:
            logger.error("Falha ao comunicar com Meta Cloud API: %s", e)
            return False, f"Erro de conexão com Meta Cloud API: {str(e)}"

    async def send_buttons(
        self,
        to_phone: str,
        text: str,
        buttons: List[WhatsAppButton],
    ) -> Tuple[bool, str]:
        clean_phone = clean_phone_number(to_phone)
        # Meta permite até 3 botões em mensagens interativas
        meta_buttons = [
            {
                "type": "reply",
                "reply": {
                    "id": b.id,
                    "title": b.title[:20],  # Limite oficial da Meta é de 20 caracteres por título de botão
                },
            }
            for b in buttons[:3]
        ]

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text},
                "action": {"buttons": meta_buttons},
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self.base_url, json=payload, headers=self._headers())
                if res.status_code in (200, 201):
                    return True, "Botões enviados via Meta Cloud API."
                logger.warning("Falha ao enviar botões interativos na Meta API: %s. Tentando texto puro.", res.text[:150])
        except Exception as e:
            logger.error("Erro ao enviar botões na Meta Cloud API: %s", e)

        # Fallback para texto puro caso o cliente esteja em versão incompatível
        options_text = "\n".join([f"👉 *{b.id}*: {b.title}" for b in buttons])
        return await self.send_text(clean_phone, f"{text}\n\n{options_text}")

    async def send_template(
        self,
        to_phone: str,
        template_name: str,
        language: str = "pt_BR",
        components: Optional[List[dict]] = None,
    ) -> Tuple[bool, str]:
        clean_phone = clean_phone_number(to_phone)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components or [],
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self.base_url, json=payload, headers=self._headers())
                if res.status_code in (200, 201):
                    return True, f"Template '{template_name}' enviado via Meta Cloud API."
                err_msg = f"Meta Cloud API erro template HTTP {res.status_code}: {res.text[:150]}"
                logger.error(err_msg)
                return False, err_msg
        except Exception as e:
            logger.error("Falha ao enviar template Meta Cloud API: %s", e)
            return False, f"Erro ao enviar template Meta: {str(e)}"
