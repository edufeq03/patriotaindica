from datetime import datetime
from typing import Any, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from backend.app.core.validators import BRAZIL_STATES, INSTAGRAM_REGEX, validate_cnpj, validate_cpf
from backend.app.schemas.category import CategoryOut


class BusinessBase(BaseModel):
    name: str
    description: Optional[str] = None
    listing_type: Literal["service", "product", "both"] = "service"

    # Contatos
    whatsapp: str
    phone: Optional[str] = None
    website: Optional[str] = None
    instagram: Optional[str] = None

    # Localização
    street: Optional[str] = None
    number: Optional[str] = None
    neighborhood: str
    city: str
    state: str = Field(..., max_length=2)
    postal_code: Optional[str] = None
    show_full_address: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    service_mode: Literal["at_location", "at_customer", "both", "online"] = "at_location"
    service_radius_km: Optional[int] = None
    serves_at_location: bool = True
    serves_at_customer: bool = False
    serves_online: bool = False

    logo_url: Optional[str] = None
    banner_url: Optional[str] = None


class BusinessPublicCard(BaseModel):
    """
    Card público para listagem e busca.
    SEGURANÇA (H6): Telefones e WhatsApp são ocultados dos cards e listagens
    para impedir raspagem em massa (scraping). O contato é feito através de
    interação com o link de redirecionamento seguro /go ou na página do perfil.
    """
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    listing_type: str
    service_mode: str
    service_radius_km: Optional[int] = None
    serves_at_location: Optional[bool] = True
    serves_at_customer: Optional[bool] = False
    serves_online: Optional[bool] = False
    category_name: Optional[str] = None
    neighborhood: str
    city: str
    state: str
    street: Optional[str] = None
    number: Optional[str] = None
    show_full_address: bool
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    is_verified: bool
    distance_km: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class BusinessDetail(BaseModel):
    """
    Perfil detalhado de visualização única da empresa.
    """
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    listing_type: str
    service_mode: str
    service_radius_km: Optional[int] = None
    serves_at_location: Optional[bool] = True
    serves_at_customer: Optional[bool] = False
    serves_online: Optional[bool] = False
    whatsapp: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    instagram: Optional[str] = None
    neighborhood: str
    city: str
    state: str
    street: Optional[str] = None
    number: Optional[str] = None
    show_full_address: bool
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    is_verified: bool
    categories: List[CategoryOut] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BusinessApplicationCreate(BaseModel):
    """
    Payload de candidatura pública.
    SEGURANÇA (M3, H2):
    - extra='forbid'
    - Validação de UFs brasileiras
    - Validação de formato de Instagram e CNPJ/CPF
    - Limite de até 3 categorias por empresa
    - Campo honeypot anti-bot
    """
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    listing_type: Literal["service", "product", "both"] = "service"
    document_type: Optional[Literal["CNPJ", "CPF"]] = "CNPJ"
    document_number: Optional[str] = Field(None, max_length=20)
    whatsapp: str = Field(..., min_length=8, max_length=20)
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    instagram: Optional[str] = Field(None, max_length=100)
    street: Optional[str] = Field(None, max_length=150)
    number: Optional[str] = Field(None, max_length=30)
    neighborhood: str = Field(..., min_length=1, max_length=100)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=2)
    postal_code: Optional[str] = Field(None, max_length=10)
    show_full_address: bool = False
    service_mode: Optional[Literal["at_location", "at_customer", "both", "online"]] = "at_location"
    service_radius_km: Optional[int] = Field(None, ge=1, le=150)
    serves_at_location: bool = True
    serves_at_customer: bool = False
    serves_online: bool = False
    category_ids: List[UUID] = Field(default_factory=list, max_length=3)
    primary_category_id: Optional[UUID] = None
    # Campo para propor novo nicho dinâmico (Sec. 4)
    proposed_niche: Optional[str] = Field(None, max_length=60, description="Novo nicho proposto caso não exista nas categorias")
    # Código de indicação / cupom amigo (Member-Get-Member)
    referred_by_code: Optional[str] = Field(None, max_length=50, description="Código ou link de indicação da empresa parceira")
    # Campo Honeypot anti-bot (se preenchido por bot, é rejeitado)
    website_url_hp: Optional[str] = Field(None, description="Honeypot field")
    # Consentimentos LGPD obrigatórios (T1.6)
    consent_carta_principios: bool = Field(..., description="Aceite obrigatório da Carta de Princípios")
    consent_termos: bool = Field(..., description="Aceite obrigatório dos Termos de Serviço")
    consent_privacidade: bool = Field(..., description="Aceite obrigatório da Política de Privacidade")

    model_config = ConfigDict(extra="forbid")

    @field_validator("consent_carta_principios", "consent_termos", "consent_privacidade")
    @classmethod
    def validate_consents(cls, v: bool) -> bool:
        if not v:
            raise ValueError("O consentimento explícito é obrigatório para cadastrar o negócio na plataforma.")
        return v

    @field_validator("proposed_niche")
    @classmethod
    def validate_niche(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        from backend.app.core.niche_validator import validate_and_normalize_niche_name
        return validate_and_normalize_niche_name(v)

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        uf = v.upper().strip()
        if uf not in BRAZIL_STATES:
            raise ValueError(f"Estado (UF) inválido: '{v}'. Use uma das 27 UFs do Brasil.")
        return uf

    @field_validator("instagram")
    @classmethod
    def validate_instagram_handle(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = v.strip().lstrip("@")
        if clean and not INSTAGRAM_REGEX.match(clean):
            raise ValueError("Usuário do Instagram inválido. Use apenas letras, números, ponto e sublinhado.")
        return clean

    @field_validator("document_number")
    @classmethod
    def validate_document(cls, v: Optional[str], info) -> Optional[str]:
        if not v:
            return None
        digits = "".join(filter(str.isdigit, v))
        doc_type = info.data.get("document_type", "CNPJ")
        if doc_type == "CPF":
            if not validate_cpf(digits):
                raise ValueError("Número de CPF com dígitos verificadores inválidos.")
        elif doc_type == "CNPJ":
            if not validate_cnpj(digits):
                raise ValueError("Número de CNPJ com dígitos verificadores inválidos.")
        return digits

    @model_validator(mode="after")
    def validate_attendance_and_honeypot(self) -> "BusinessApplicationCreate":
        if self.website_url_hp and self.website_url_hp.strip():
            raise ValueError("Acesso não permitido (spam detectado).")

        # Se o chamador forneceu os campos booleanos de atendimento explicitamente:
        attendance_fields = {"serves_at_location", "serves_at_customer", "serves_online"}
        if attendance_fields.intersection(self.model_fields_set):
            if not (self.serves_at_location or self.serves_at_customer or self.serves_online):
                raise ValueError("Selecione ao menos um método de atendimento.")
        else:
            # Chamador legado (baseado apenas em service_mode)
            if self.service_mode == "at_customer":
                self.serves_at_customer = True
                self.serves_at_location = False
            elif self.service_mode == "both":
                self.serves_at_location = True
                self.serves_at_customer = True
            elif self.service_mode == "online":
                self.serves_online = True
                self.serves_at_location = False
            else:
                self.serves_at_location = True

        # Sincronizar service_mode
        if self.serves_at_customer and self.serves_at_location:
            self.service_mode = "both"
        elif self.serves_at_customer:
            self.service_mode = "at_customer"
        elif self.serves_online and not self.serves_at_location:
            self.service_mode = "online"
        else:
            self.service_mode = "at_location"

        return self


class BusinessRegisterCreate(BusinessApplicationCreate):
    """
    T1.1: Cadastro único e atômico (Dono + Empresa).
    Cria conta de usuário (role='owner') e empresa associada na mesma transação.
    Aceita formato plano (flat) ou formato estruturado ({ owner, business, consents }).
    """
    owner_name: str = Field(..., min_length=2, max_length=150, description="Nome completo do responsável/proprietário")
    owner_email: EmailStr = Field(..., description="E-mail profissional ou de acesso do proprietário")
    owner_password: str = Field(..., min_length=10, max_length=100, description="Senha de acesso ao painel (mínimo 10 caracteres)")
    owner_phone: Optional[str] = Field(None, max_length=25, description="Telefone pessoal ou secundário do proprietário")

    @model_validator(mode="before")
    @classmethod
    def flatten_nested_payload(cls, data: Any) -> Any:
        if isinstance(data, dict) and ("business" in data or "owner" in data or "consents" in data):
            flat = {}
            if isinstance(data.get("business"), dict):
                flat.update(data["business"])
            if isinstance(data.get("owner"), dict):
                owner = data["owner"]
                if "name" in owner and "owner_name" not in flat:
                    flat["owner_name"] = owner["name"]
                if "email" in owner and "owner_email" not in flat:
                    flat["owner_email"] = owner["email"]
                if "password" in owner and "owner_password" not in flat:
                    flat["owner_password"] = owner["password"]
                if "phone" in owner and "owner_phone" not in flat:
                    flat["owner_phone"] = owner["phone"]
            if isinstance(data.get("consents"), dict):
                flat.update(data["consents"])
            # Preserva quaisquer campos de primeiro nível não aninhados
            for k, v in data.items():
                if k not in ("owner", "business", "consents") and k not in flat:
                    flat[k] = v
            return flat
        return data


class ReportCreate(BaseModel):
    """
    Submissão de denúncia (H2).
    - reason e details com limites
    - Honeypot anti-bot
    - extra='forbid'
    """
    reason: str = Field(..., min_length=3, max_length=100)
    details: Optional[str] = Field(None, max_length=1000)
    contact_email: Optional[EmailStr] = None
    website_url_hp: Optional[str] = Field(None, description="Honeypot field")

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def check_honeypot(self) -> "ReportCreate":
        if self.website_url_hp and self.website_url_hp.strip():
            raise ValueError("Acesso não permitido (spam detectado).")
        return self
