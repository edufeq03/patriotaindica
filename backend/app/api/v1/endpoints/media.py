from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from backend.app.core.rate_limit import check_rate_limit, get_client_ip
from backend.app.core.security import get_current_user
from backend.app.models.user import User
from backend.app.services.media import process_and_save_image

router = APIRouter()


@router.post("/upload")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    SEGURANÇA (M10): Upload próprio de imagens (logo e banner).
    - Validação de magic bytes (JPEG, PNG, WEBP).
    - Rejeição de SVG (mitigação de XSS).
    - Re-encode com Pillow (limpeza de metadados e scripts embutidos).
    - Rate limit de 10 uploads por hora.
    """
    client_ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ratelimit:upload:{client_ip}",
        limit=10,
        window_seconds=3600,
        error_msg="Limite de 10 uploads por hora atingido.",
    )

    file_url = await process_and_save_image(file)
    return {
        "success": True,
        "url": file_url,
    }
