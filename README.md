# 📝 Proyecto Keyoku — Asistente de Planificación Docente con IA
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

## 📄 Licencia
Proyecto educativo y libre. Desarrollado por **MarC**.
