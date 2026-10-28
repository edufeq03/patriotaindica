import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger("patriotaindica.whatsapp")


@dataclass
class WhatsAppButton:
    id: str
    title: str


def clean_phone_number(phone: str) -> str:
    """Extrai apenas dígitos e garante DDI 55 para números brasileiros."""
    clean = "".join(filter(str.isdigit, phone))
    if not clean.startswith("55") and len(clean) in (10, 11):
        clean = f"55{clean}"
    return clean


class WhatsAppProvider(ABC):
    """
    Interface abstrata comum para o Provedor de WhatsApp (Padrão Strategy / Driver).
    Permite operar tanto em modo não-oficial (Evolution API) quanto oficial (Meta Cloud API).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def send_text(self, to_phone: str, text: str) -> Tuple[bool, str]:
        """Envia mensagem de texto simples."""
        pass

    @abstractmethod
    async def send_buttons(
        self,
        to_phone: str,
        text: str,
        buttons: List[WhatsAppButton],
    ) -> Tuple[bool, str]:
        """Envia mensagem interativa com botões de ação rápida."""
        pass

    @abstractmethod
    async def send_template(
        self,
        to_phone: str,
        template_name: str,
        language: str = "pt_BR",
        components: Optional[List[dict]] = None,
    ) -> Tuple[bool, str]:
        """Envia template oficial da Meta (ou texto equivalente na Evolution)."""
        pass
