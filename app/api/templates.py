"""Endpoints para gestión de plantillas institucionales de Word (.docx)."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_optional_current_user
from app.export.template_manager import (
    create_base_model_template,
    get_user_template_name,
    get_user_template_path,
    remove_user_template,
    save_user_template,
)
from app.models.user import User

router = APIRouter(prefix="/templates", tags=["Plantillas Institucionales"])


@router.get("/status", summary="Consultar estado de la plantilla")
async def template_status(
    current_user: User | None = Depends(get_optional_current_user),
):
    """Indica si el docente tiene activa una plantilla personalizada con su logo."""
    user_id = current_user.id if current_user else 1
    custom_path = get_user_template_path(user_id)
    template_name = get_user_template_name(user_id)

    return {
        "has_custom_template": custom_path is not None,
        "template_name": template_name or "Plantilla Estándar Kantan",
    }


@router.post("/upload", summary="Subir plantilla institucional con logo")
async def upload_template(
    file: UploadFile = File(...),
    current_user: User | None = Depends(get_optional_current_user),
):
    """Permite al docente subir su archivo .docx con el logo y membrete de su escuela."""
    filename = file.filename or "plantilla.docx"
    if not filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La plantilla debe ser un archivo en formato Word (.docx).",
        )

    user_id = current_user.id if current_user else 1
    content = await file.read()

    try:
        saved_path = save_user_template(user_id, content, filename)
        return {
            "status": "success",
            "message": f"Plantilla institucional '{filename}' guardada exitosamente.",
            "template_name": filename,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar la plantilla: {e}",
        )


@router.get("/model", summary="Descargar plantilla editable con etiquetas")
async def download_model_template():
    """Descarga un archivo .docx base listo para que el docente pegue el logo de su escuela."""
    model_path = create_base_model_template()
    return FileResponse(
        path=str(model_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="Plantilla_Modelo_Kantan_Con_Logo.docx",
    )


@router.delete("", summary="Restablecer a plantilla predeterminada")
async def reset_template(
    current_user: User | None = Depends(get_optional_current_user),
):
    """Elimina la plantilla personalizada y vuelve a la plantilla estándar."""
    user_id = current_user.id if current_user else 1
    removed = remove_user_template(user_id)
    return {
        "status": "success",
        "message": "Plantilla restablecida a la predeterminada.",
        "removed": removed,
    }
