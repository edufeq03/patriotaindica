import logging
from typing import List, Optional, Tuple
import httpx

from backend.app.services.whatsapp.base import WhatsAppButton, WhatsAppProvider, clean_phone_number

logger = logging.getLogger("patriotaindica.whatsapp.evolution")


class EvolutionWhatsAppProvider(WhatsAppProvider):
    """
    Driver para a Evolution API (WhatsApp self-hosted via Baileys).
    Custo zero de Meta, ativação instantânea com QR Code.
    """

    def __init__(self, base_url: str, api_key: str, instance_name: str):
        cleaned_url = base_url.strip().rstrip("/")
        if cleaned_url.endswith("/manager"):
            cleaned_url = cleaned_url[:-8].rstrip("/")
        self.base_url = cleaned_url
        self.api_key = api_key.strip()
        self.instance_name = instance_name.strip()

    @property
    def provider_name(self) -> str:
        return "evolution"

    def _headers(self) -> dict:
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    async def send_text(self, to_phone: str, text: str) -> Tuple[bool, str]:
        clean_phone = clean_phone_number(to_phone)
        url = f"{self.base_url}/message/sendText/{self.instance_name}"

        payload_v2 = {
            "number": clean_phone,
            "text": text,
        }
        payload_v1 = {
            "number": clean_phone,
            "textMessage": {"text": text},
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload_v2, headers=self._headers())
                if res.status_code in (200, 201):
                    logger.info("WhatsApp enviado via Evolution API para %s com sucesso.", clean_phone)
                    return True, "Mensagem enviada com sucesso via Evolution API."

                if res.status_code == 400:
                    res_v1 = await client.post(url, json=payload_v1, headers=self._headers())
                    if res_v1.status_code in (200, 201):
                        logger.info("WhatsApp enviado via Evolution API (v1) para %s.", clean_phone)
                        return True, "Mensagem enviada com sucesso via Evolution API."

                err_msg = f"Evolution API retornou HTTP {res.status_code}: {res.text[:150]}"
                logger.error(err_msg)
                return False, err_msg
        except Exception as e:
            logger.error("Falha ao comunicar com Evolution API: %s", e)
            return False, f"Erro de conexão com Evolution API: {str(e)}"

    async def send_buttons(
        self,
        to_phone: str,
        text: str,
        buttons: List[WhatsAppButton],
    ) -> Tuple[bool, str]:
        """
        Envia mensagem interativa com botões. Caso a instância Baileys não suporte
        botões interativos na versão instalada, formata as opções em texto numerado com instruções.
        """
        clean_phone = clean_phone_number(to_phone)
        url = f"{self.base_url}/message/sendButtons/{self.instance_name}"

        payload = {
            "number": clean_phone,
            "title": "Patriota Indica",
            "description": text,
            "buttons": [{"id": b.id, "text": b.title} for b in buttons],
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload, headers=self._headers())
                if res.status_code in (200, 201):
                    return True, "Botões enviados via Evolution API."
        except Exception:
            pass

        # Fallback de alta confiabilidade: Formata em texto com opções numeradas
        options_text = "\n".join([f"👉 *{b.id}*: {b.title}" for b in buttons])
        fallback_msg = f"{text}\n\n{options_text}\n\n_Responda com o código da opção desejada._"
        return await self.send_text(to_phone=clean_phone, text=fallback_msg)

    async def send_template(
        self,
        to_phone: str,
        template_name: str,
        language: str = "pt_BR",
        components: Optional[List[dict]] = None,
    ) -> Tuple[bool, str]:
        """
        Na Evolution API, converte os parâmetros do template em mensagem formatada direta.
        """
        text_lines = [f"📢 *Patriota Indica* ({template_name})"]
        if components:
            for comp in components:
                for param in comp.get("parameters", []):
                    if param.get("type") == "text":
                        text_lines.append(str(param.get("text", "")))
        full_text = "\n\n".join(text_lines)
        return await self.send_text(to_phone=to_phone, text=full_text)
