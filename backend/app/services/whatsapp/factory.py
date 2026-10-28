import logging
from typing import List, Optional, Tuple

from backend.app.core.config import settings
from backend.app.services.whatsapp.base import WhatsAppButton, WhatsAppProvider
from backend.app.services.whatsapp.evolution import EvolutionWhatsAppProvider
from backend.app.services.whatsapp.meta_cloud import MetaCloudWhatsAppProvider

logger = logging.getLogger("patriotaindica.whatsapp.factory")


class ConsoleWhatsAppProvider(WhatsAppProvider):
    """
    Driver para testes locais e desenvolvimento offline sem dependência externa.
    Registra os disparos no log da aplicação.
    """

    @property
    def provider_name(self) -> str:
        return "console"

    async def send_text(self, to_phone: str, text: str) -> Tuple[bool, str]:
        logger.info("[WHATSAPP MOCK TXT] Para: %s | Texto:\n%s", to_phone, text)
        return True, "Mensagem simulada enviada para o console."

    async def send_buttons(
        self,
        to_phone: str,
        text: str,
        buttons: List[WhatsAppButton],
    ) -> Tuple[bool, str]:
        btn_str = ", ".join([f"[{b.id}: {b.title}]" for b in buttons])
        logger.info("[WHATSAPP MOCK BTN] Para: %s | Texto: %s | Botões: %s", to_phone, text, btn_str)
        return True, "Botões simulados enviados para o console."

    async def send_template(
        self,
        to_phone: str,
        template_name: str,
        language: str = "pt_BR",
        components: Optional[List[dict]] = None,
    ) -> Tuple[bool, str]:
        logger.info("[WHATSAPP MOCK TPL] Para: %s | Template: %s | Params: %s", to_phone, template_name, components)
        return True, f"Template '{template_name}' simulado enviado para o console."


def get_whatsapp_service() -> WhatsAppProvider:
    """
    Factory que instancia o driver correto de WhatsApp conforme a configuração:
    1. 'meta_cloud': Se configurado e com token presente
    2. 'evolution': Se configurado com Evolution API ativa
    3. 'console': Fallback para desenvolvimento e testes
    """
    provider_type = (settings.WHATSAPP_PROVIDER or "evolution").lower().strip()

    if provider_type == "meta_cloud":
        if settings.META_WHATSAPP_ACCESS_TOKEN and settings.META_WHATSAPP_PHONE_NUMBER_ID:
            return MetaCloudWhatsAppProvider(
                access_token=settings.META_WHATSAPP_ACCESS_TOKEN,
                phone_number_id=settings.META_WHATSAPP_PHONE_NUMBER_ID,
            )
        logger.warning("WHATSAPP_PROVIDER está 'meta_cloud' mas faltam tokens da Meta. Usando fallback Console.")
        return ConsoleWhatsAppProvider()

    if provider_type == "evolution":
        if settings.EVOLUTION_API_URL and settings.EVOLUTION_API_KEY and settings.EVOLUTION_INSTANCE_NAME:
            return EvolutionWhatsAppProvider(
                base_url=settings.EVOLUTION_API_URL,
                api_key=settings.EVOLUTION_API_KEY,
                instance_name=settings.EVOLUTION_INSTANCE_NAME,
            )
        logger.warning("WHATSAPP_PROVIDER está 'evolution' mas faltam credenciais da Evolution. Usando fallback Console.")
        return ConsoleWhatsAppProvider()

    return ConsoleWhatsAppProvider()
