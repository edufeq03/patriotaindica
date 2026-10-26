import re
import unicodedata

# Apenas letras latinas (com acentuação em português), números, espaço, -, &, ', .
NICHE_ALLOWED_PATTERN = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ0-9\s\-&'\.]+$")
REPETITIVE_PATTERN = re.compile(r"(.)\1{3,}")  # 4 ou mais caracteres repetidos seguidos
URL_OR_EMAIL_PATTERN = re.compile(r"(https?://|www\.|\.com|\.br|@)", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(\(?\d{2}\)?\s*9?\d{4}[-\s]?\d{4})")


def validate_and_normalize_niche_name(name: str) -> str:
    """
    Validação e normalização de nome de nicho dinâmico (Seção 4.2 do Relatório):
    - 3 a 60 caracteres
    - Normalização Unicode NFKC (elimina homógrafos cirílicos e caracteres invisíveis)
    - Rejeita URLs, e-mails, telefones, repetições excessivas ('aaaa') e números puros
    - Normaliza espaços múltiplos
    """
    if not name:
        raise ValueError("O nome do nicho é obrigatório.")

    # 1. Normalização Unicode NFKC
    normalized = unicodedata.normalize("NFKC", name).strip()
    normalized = re.sub(r"\s+", " ", normalized)

    # 2. Tamanho
    if len(normalized) < 3:
        raise ValueError("O nome do nicho deve ter pelo menos 3 caracteres.")
    if len(normalized) > 60:
        raise ValueError("O nome do nicho deve ter no máximo 60 caracteres.")

    # 3. Caracteres permitidos (elimina homógrafos cirílicos e injeções)
    if not NICHE_ALLOWED_PATTERN.match(normalized):
        raise ValueError("O nome contém caracteres inválidos. Use apenas letras, números e pontuação simples.")

    # 4. Rejeição de repetições excessivas
    if REPETITIVE_PATTERN.search(normalized):
        raise ValueError("O nome contém repetições excessivas de caracteres.")

    # 5. Rejeição de números puros
    if normalized.replace(" ", "").isdigit():
        raise ValueError("O nome do nicho não pode ser composto apenas por números.")

    # 6. Rejeição de URLs, emails ou telefones
    if URL_OR_EMAIL_PATTERN.search(normalized) or PHONE_PATTERN.search(normalized):
        raise ValueError("O nome do nicho não pode conter links, e-mails ou números de telefone.")

    return normalized
