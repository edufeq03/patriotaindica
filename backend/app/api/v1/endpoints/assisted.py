import csv
import io
import secrets
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.csv_sanitizer import sanitize_csv_cell
from backend.app.core.database import get_db
from backend.app.core.security import get_current_active_admin
from backend.app.models.business import Business
from backend.app.models.events import BusinessReviewLog
from backend.app.models.user import User
from backend.app.schemas.business import BusinessApplicationCreate
from backend.app.services.geocoding import geocode_address

router = APIRouter()

MAX_CSV_SIZE = 2 * 1024 * 1024  # 2 MB (M13)
MAX_CSV_ROWS = 2000  # Máx 2000 linhas (M13)


@router.post("/csv", status_code=status.HTTP_200_OK)
async def import_businesses_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    """
    SEGURANÇA (M13): Importação em lote via CSV com proteção contra Injeção de Fórmulas.
    - Limite de 2 MB e 2.000 linhas.
    - Sanitização contra CSV/Formula Injection (=, +, -, @ neutralizados).
    - Validação por linha com schema de candidatura.
    - Inserção obrigatória com status='pending_review' e source='csv_assisted'.
    - Relatório detalhado de sucessos e erros por linha.
    """
    content = await file.read()

    if len(content) > MAX_CSV_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo CSV excede o limite máximo de 2 MB.",
        )

    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            decoded = content.decode("latin-1")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Codificação de arquivo inválida. Salve o CSV como UTF-8.",
            )

    csv_reader = csv.DictReader(io.StringIO(decoded))
    if not csv_reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV vazio ou sem cabeçalhos válidos.")

    imported_count = 0
    errors: List[Dict[str, Any]] = []

    rows = list(csv_reader)
    if len(rows) > MAX_CSV_ROWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O CSV contém {len(rows)} linhas. O limite máximo permitido é de {MAX_CSV_ROWS} linhas.",
        )

    for line_idx, row in enumerate(rows, start=2):  # Linha 1 é o cabeçalho
        # Sanitizar injeção de fórmulas em todas as células (M13)
        sanitized_row = {k: sanitize_csv_cell(v) for k, v in row.items() if k}

        try:
            # Mapear colunas do CSV para o schema
            payload_data = {
                "name": sanitized_row.get("name") or sanitized_row.get("nome"),
                "description": sanitized_row.get("description") or sanitized_row.get("descricao"),
                "whatsapp": sanitized_row.get("whatsapp") or sanitized_row.get("telefone"),
                "phone": sanitized_row.get("phone"),
                "document_type": sanitized_row.get("document_type") or "CNPJ",
                "document_number": sanitized_row.get("document_number") or sanitized_row.get("cnpj"),
                "neighborhood": sanitized_row.get("neighborhood") or sanitized_row.get("bairro") or "Centro",
                "city": sanitized_row.get("city") or sanitized_row.get("cidade"),
                "state": sanitized_row.get("state") or sanitized_row.get("uf"),
                "postal_code": sanitized_row.get("postal_code") or sanitized_row.get("cep"),
                "service_mode": sanitized_row.get("service_mode") or "at_location",
                "service_radius_km": int(sanitized_row.get("service_radius_km", 20)) if sanitized_row.get("service_radius_km") else None,
            }

            # Validar linha com o mesmo schema rigoroso da candidatura
            valid_app = BusinessApplicationCreate(**payload_data)

            # Geocodificar no servidor sem padrão de Campinas
            lat, lng, geo_source, geo_conf = await geocode_address(
                postal_code=valid_app.postal_code,
                city=valid_app.city,
                state=valid_app.state,
            )
            location_geog = f"SRID=4326;POINT({lng} {lat})" if lat and lng else None

            slug_base = f"{valid_app.name.lower().replace(' ', '-')}-{valid_app.city.lower().replace(' ', '-')}"
            slug = f"{slug_base[:160]}-{secrets.token_hex(2)}"

            new_biz = Business(
                name=valid_app.name,
                slug=slug,
                description=valid_app.description,
                listing_type=valid_app.listing_type,
                document_type=valid_app.document_type,
                document_number=valid_app.document_number,
                whatsapp=valid_app.whatsapp,
                phone=valid_app.phone,
                neighborhood=valid_app.neighborhood,
                city=valid_app.city,
                state=valid_app.state,
                postal_code=valid_app.postal_code,
                location=location_geog,
                geocode_source=geo_source,
                geocode_confidence=geo_conf,
                service_mode=valid_app.service_mode,
                service_radius_km=valid_app.service_radius_km,
                status="pending_review",  # REGRA: SEMPRE PENDENTE DE CURADORIA
                source="csv_assisted",
                is_verified=False,
            )
            db.add(new_biz)
            await db.flush()

            # Log de auditoria
            review_log = BusinessReviewLog(
                business_id=new_biz.id,
                from_status=None,
                to_status="pending_review",
                note=f"Importado via lote CSV pelo administrador {current_admin.name}. Aguardando triagem.",
                admin_id=current_admin.id,
            )
            db.add(review_log)
            imported_count += 1

        except ValidationError as ve:
            errors.append({"line": line_idx, "error": str(ve.errors()[0]["msg"])})
        except Exception as e:
            errors.append({"line": line_idx, "error": str(e)})

    await db.commit()

    return {
        "success": True,
        "total_rows": len(rows),
        "imported": imported_count,
        "errors_count": len(errors),
        "errors": errors[:50],  # Primeiros 50 erros para diagnóstico
    }
