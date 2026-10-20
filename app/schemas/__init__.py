"""Schemas Pydantic - Paquete.

Re-exporta todos los schemas para acceso conveniente.
"""

from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserInDB
from app.schemas.auth import LoginRequest, TokenResponse, TokenPayload
from app.schemas.document import DocumentUpload, DocumentResponse, DocumentListResponse
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionListResponse,
)
from app.schemas.plan import (
    ActividadSecuencia,
    SecuenciaDidactica,
    DatosGenerales,
    Evaluacion,
    PlanDiario,
    PlanGeneratedResponse,
)

__all__ = [
    # Usuario
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    # Auth
    "LoginRequest",
    "TokenResponse",
    "TokenPayload",
    # Documento
    "DocumentUpload",
    "DocumentResponse",
    "DocumentListResponse",
    # Chat
    "ChatSessionCreate",
    "ChatSessionResponse",
    "ChatMessageCreate",
    "ChatMessageResponse",
    "ChatSessionListResponse",
    # Plan
    "ActividadSecuencia",
    "SecuenciaDidactica",
    "DatosGenerales",
    "Evaluacion",
    "PlanDiario",
    "PlanGeneratedResponse",
]
