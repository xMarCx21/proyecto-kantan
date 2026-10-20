# 📝 Proyecto Kantan — Asistente de Planificación Docente con IA
*Made with ❤️ by MarC*

Aplicación web diseñada para profesores y docentes que automatiza la creación de **Planes Diarios de Clase** utilizando Inteligencia Artificial (**Google Gemini 2.0**) y un sistema de recuperación documental (**RAG** con ChromaDB). Permite subir planificaciones de años anteriores en Word (.docx), seleccionarlas como contexto pedagógico, interactuar mediante un chat moderno e intuitivo y descargar el resultado final listo en formato Word (.docx).

---

## ✨ Características Principales

- 💬 **Interfaz Moderna estilo Gemini**: Diseñada para docentes, limpia, ágil y con soporte para **Modo Oscuro / Modo Claro**.
- 📚 **Contexto RAG de Planes Anteriores**: Sube archivos `.docx` de ciclos lectivos pasados; Kantan los indexa y los toma como modelo pedagógico.
- ⚡ **Streaming de Respuesta en Vivo**: Las planificaciones se generan en tiempo real con estructura didáctica completa:
  - Objetivo pedagógico
  - Contenidos y saberes
  - **Secuencia Didáctica**: Inicio, Desarrollo y Cierre (con tiempos sugeridos y actividades)
  - Recursos y materiales
  - Evaluación y criterios de logro
- 📥 **Exportación Profesional a Word (.docx)**: Descarga directa con formato institucional, tablas y diseño listo para imprimir o presentar.
- 🔐 **Arquitectura Segura y Modular**: Desarrollada sobre FastAPI, SQLAlchemy 2.0 Async, Pydantic v2 y autenticación JWT.

---

## 🚀 Despliegue Rápido en Render.com (Plan Gratuito)

Este proyecto está preparado para desplegarse con **Docker** en 1 clic:

1. Crea una cuenta en [Render.com](https://render.com).
2. Haz clic en **New +** y selecciona **Web Service**.
3. Conecta este repositorio de GitHub.
4. Render detectará automáticamente el archivo `Dockerfile`.
5. En la sección **Environment Variables**, añade:
   - `GEMINI_API_KEY`: Tu clave de Google AI Studio.
   - `APP_ENV`: `production`
6. Haz clic en **Create Web Service** y obtén tu URL pública permanente con HTTPS.

---

## 💻 Ejecución Local

### 1. Clonar el repositorio
```bash
git clone https://github.com/TU_USUARIO/proyecto-kantan.git
cd proyecto-kantan
```

### 2. Crear y activar entorno virtual
```bash
python -m venv .venv
# En Windows:
.\.venv\Scripts\Activate.ps1
# En Linux/Mac:
source .venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Copia el archivo `.env.example` a `.env` y añade tu `GEMINI_API_KEY`:
```bash
cp .env.example .env
```

### 5. Iniciar la aplicación
```bash
uvicorn app.main:app --reload
```
Abre en tu navegador: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🧪 Pruebas Automatizadas

```bash
pytest tests/ -v
```

---

## 📄 Licencia
Proyecto educativo y libre. Desarrollado por **MarC**.
