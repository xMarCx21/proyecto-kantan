"""Punto de entrada principal para la aplicación FastAPI de Proyecto Kantan."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.config import get_settings
from app.db import Base, engine

settings = get_settings()
TEMPLATES_DIR = Path(__file__).parent / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestor del ciclo de vida de la aplicación.

    Crea las tablas en la base de datos si no existen al iniciar.
    """
    # Crear carpetas necesarias
    settings.upload_path
    settings.generated_path
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)

    # Inicializar tablas en SQLite
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Limpieza en apagado
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Aplicación web para automatizar la creación de Planes Diarios de clase con IA y RAG.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware CORS (útil para desarrollo) ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers de la API ──
app.include_router(auth_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


# ── Interfaz Principal (Estilo Gemini) ──
@app.get("/", response_class=HTMLResponse, tags=["Interfaz"])
async def index_view():
    """Sirve la interfaz web conversacional tipo Gemini para docentes."""
    html_file = TEMPLATES_DIR / "index.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Proyecto Kantan</h1><p>Cargando interfaz...</p>")


# ── Healthcheck & Estado ──
@app.get("/api/health", tags=["Estado"], status_code=status.HTTP_200_OK)
async def health_check():
    """Endpoint de verificación de salud del backend."""
    return {
        "status": "online",
        "app": settings.app_name,
        "environment": settings.app_env,
        "debug": settings.debug,
    }
