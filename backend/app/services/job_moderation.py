import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

# Tabela de termos padrão compilada para velocidade e fallback caso banco esteja offline
DEFAULT_MODERATION_RULES = [
    # 1. Discriminação (Block)
    ("boa aparencia", "discriminacao", "block", "phrase"),
    ("aparencia", "discriminacao", "block", "word"),
    ("foto obrigatoria", "discriminacao", "block", "phrase"),
    ("apenas mulheres", "discriminacao", "block", "phrase"),
    ("apenas homens", "discriminacao", "block", "phrase"),
    ("somente feminino", "discriminacao", "block", "phrase"),
    ("somente masculino", "discriminacao", "block", "phrase"),
    ("sexo feminino", "discriminacao", "block", "phrase"),
    ("sexo masculino", "discriminacao", "block", "phrase"),
    ("solteiro", "discriminacao", "block", "word"),
    ("solteira", "discriminacao", "block", "word"),
    ("casado", "discriminacao", "block", "word"),
    ("casada", "discriminacao", "block", "word"),
    ("sem filhos", "discriminacao", "block", "phrase"),
    ("ate 25 anos", "discriminacao", "block", "phrase"),
    ("idade entre", "discriminacao", "block", "phrase"),
    ("jovem", "discriminacao", "block", "word"),
    ("cor da pele", "discriminacao", "block", "phrase"),
    ("raca", "discriminacao", "block", "word"),
    ("etnia", "discriminacao", "block", "word"),
    # 2. Convicção Política / Religiosa (Block)
    ("de direita", "conviccao", "block", "phrase"),
    ("de esquerda", "conviccao", "block", "phrase"),
    ("alinhado politicamente", "conviccao", "block", "phrase"),
    ("partido", "conviccao", "block", "word"),
    ("cristao", "conviccao", "block", "word"),
    ("crista", "conviccao", "block", "word"),
    ("evangelico", "conviccao", "block", "word"),
    ("evangelica", "conviccao", "block", "word"),
    ("catolico", "conviccao", "block", "word"),
    ("catolica", "conviccao", "block", "word"),
    ("ateu", "conviccao", "block", "word"),
    # 3. Golpe / Cobrança do candidato (Block)
    ("taxa de inscricao", "golpe", "block", "phrase"),
    ("taxa de cadastro", "golpe", "block", "phrase"),
    ("deposito adiantado", "golpe", "block", "phrase"),
    ("pagamento adiantado", "golpe", "block", "phrase"),
    ("pix para entrevista", "golpe", "block", "phrase"),
    ("compre o kit", "golpe", "block", "phrase"),
    ("multinivel", "golpe", "block", "word"),
    ("renda extra garantida", "golpe", "block", "phrase"),
    ("trabalhe de casa ganhando", "golpe", "block", "phrase"),
    ("sem experiencia ganhe", "golpe", "block", "phrase"),
    ("ganhe dinheiro facil", "golpe", "block", "phrase"),
    # 4. Impróprio (Block)
    ("acompanhante", "improprio", "block", "word"),
    ("massagem sensual", "improprio", "block", "phrase"),
    ("conteudo adulto", "improprio", "block", "phrase"),
    # 5. Revisão Humana (Review - vaga vai para fila de triagem)
    ("disponibilidade total", "review", "review", "phrase"),
    ("boa presenca", "review", "review", "phrase"),
    ("perfil comercial agressivo", "review", "review", "phrase"),
]

# Termos que possuem amparo legal de idade/escolaridade exclusivamente para estágio e aprendiz
APPRENTICE_STAGE_EXCEPTIONS = {
    "ate 25 anos",
    "idade entre",
    "jovem",
}


@dataclass
class ModerationResult:
    is_blocked: bool = False
    block_category: Optional[str] = None
    educational_message: Optional[str] = None
    is_review: bool = False
    flags: List[str] = field(default_factory=list)


def normalize_for_moderation(text: str) -> str:
    """
    Normaliza texto para detecção de termos proibidos (Seção 5.1):
    1. Normalização Unicode NFKD para remover acentos
    2. Minúsculo
    3. Substituição de leet speak: 0->o, 1->i, 3->e, 4->a, 5->s, @->a
    4. Remoção de pontuação mantendo apenas letras, números e espaços
    5. Colapso de múltiplos espaços
    """
    if not text:
        return ""

    # Normalização e remoção de acentos
    nfkd = unicodedata.normalize("NFKD", text)
    without_accents = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()

    # Leet speak mapping
    leet_map = {
        "0": "o",
        "1": "i",
        "!": "i",
        "3": "e",
        "4": "a",
        "@": "a",
        "5": "s",
        "$": "s",
    }
    leet_converted = "".join(leet_map.get(ch, ch) for ch in without_accents)

    # Remover pontuação e manter apenas caracteres alfanuméricos e espaços
    cleaned = re.sub(r"[^a-z0-9\s]", " ", leet_converted)
    collapsed = re.sub(r"\s+", " ", cleaned).strip()
    return collapsed


def check_job_content(
    title: str,
    description: Optional[str] = None,
    contract_type: str = "clt",
    custom_rules: Optional[List[Tuple[str, str, str, str]]] = None,
) -> ModerationResult:
    """
    Aplica as regras de moderação de conteúdo (Seção 5 da especificação).
    """
    combined_raw = f"{title} {description or ''}"
    normalized_text = normalize_for_moderation(combined_raw)
    rules = custom_rules if custom_rules is not None else DEFAULT_MODERATION_RULES

    detected_flags: Set[str] = set()
    block_category: Optional[str] = None
    is_blocked = False
    is_review = False

    is_stage_or_apprentice = contract_type in ("estagio", "aprendiz")

    for term_raw, category, severity, match_type in rules:
        term_norm = normalize_for_moderation(term_raw)
        if not term_norm:
            continue

        # Exceção legal para jovem aprendiz e estágio
        if is_stage_or_apprentice and term_raw in APPRENTICE_STAGE_EXCEPTIONS:
            continue

        matched = False
        if match_type == "word":
            pattern = rf"\b{re.escape(term_norm)}\b"
            if re.search(pattern, normalized_text):
                matched = True
        else:  # 'phrase'
            if term_norm in normalized_text:
                matched = True

        if matched:
            detected_flags.add(category)
            if severity == "block":
                is_blocked = True
                if not block_category:
                    block_category = category
            elif severity == "review":
                is_review = True

    if is_blocked:
        # Mensagens educativas padronizadas (Seção 5.3)
        if block_category in ("discriminacao", "conviccao"):
            msg = (
                "Não é permitido exigir idade, sexo, estado civil, aparência, religião ou posição política. "
                "Descreva as atividades, local, horário e os requisitos profissionais da vaga."
            )
        elif block_category == "golpe":
            msg = (
                "Não é permitido cobrar taxa de inscrição, depósitos ou promessas de renda fácil. "
                "A candidatura a vagas de emprego no Patriota Indica deve ser 100% gratuita para o trabalhador."
            )
        elif block_category == "improprio":
            msg = (
                "O conteúdo da vaga viola os princípios de ética e respeito do Patriota Indica. "
                "Por favor, revise o título e a descrição."
            )
        else:
            msg = "O conteúdo informado não cumpre as diretrizes de publicação de vagas da comunidade."

        return ModerationResult(
            is_blocked=True,
            block_category=block_category,
            educational_message=msg,
            is_review=False,
            flags=sorted(list(detected_flags)),
        )

    return ModerationResult(
        is_blocked=False,
        block_category=None,
        educational_message=None,
        is_review=is_review,
        flags=sorted(list(detected_flags)),
    )
