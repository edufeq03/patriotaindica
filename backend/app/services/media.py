import io
import os
import uuid
from typing import Tuple
from fastapi import HTTPException, UploadFile, status
from PIL import Image

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB (M10)

# Assinaturas binárias (Magic Bytes)
ALLOWED_MAGIC_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # Formato RIFF (WEBP)
}

UPLOAD_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../static/uploads")
)


def validate_magic_bytes(content: bytes) -> str:
    """
    SEGURANÇA (M10): Validação de arquivo real por assinatura binária (magic bytes).
    Nunca confia no Content-Type enviado pelo navegador nem na extensão.
    SVG é explicitamente rejeitado para mitigar vetores de XSS.
    """
    if len(content) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo corrompido ou muito pequeno.",
        )

    # Rejeitar arquivos SVG explicitamente (contêm XML e execução de scripts)
    content_head = content[:200].lower()
    if b"<svg" in content_head or b"<?xml" in content_head:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato SVG não permitido por razões de segurança (vetor de script).",
        )

    # Verificar magic bytes
    if content.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    elif content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "WEBP"

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Formato de imagem inválido ou não suportado. Envie apenas JPEG, PNG ou WEBP.",
    )


async def process_and_save_image(file: UploadFile) -> str:
    """
    SEGURANÇA (M10):
    1. Validação de tamanho (máx 2 MB).
    2. Validação por magic bytes.
    3. Re-encode com Pillow (elimina metadados EXIF, GPS e payloads embutidos).
    4. Gravação com nome pseudoaleatório seguro.
    """
    content = await file.read()

    # 1. Validar tamanho
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo excede o limite máximo permitido de 2 MB.",
        )

    # 2. Validar Magic Bytes
    image_format = validate_magic_bytes(content)

    # 3. Re-encode com Pillow para sanitização completa
    try:
        img = Image.open(io.BytesIO(content))
        # Converter para RGB se for RGBA/P e for salvar como JPEG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Redimensionar suavemente se for excessivamente grande (ex: banner 4k)
        max_dim = 1600
        if img.width > max_dim or img.height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        # 4. Criar diretório de upload se não existir
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Salva como JPEG com compressão otimizada e sem metadados
        img.save(filepath, format="JPEG", quality=85, optimize=True)

        return f"/static/uploads/{filename}"

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível processar a imagem enviada.",
        )
