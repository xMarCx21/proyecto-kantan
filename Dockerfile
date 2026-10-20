# Imagen base liviana de Python 3.12
FROM python:3.12-slim

# Evitar que Python escriba archivos .pyc y forzar salida en tiempo real en consola
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Crear directorios para archivos
RUN mkdir -p uploads generated chroma_data

# Exponer el puerto de FastAPI
EXPOSE 8000

# Comando para iniciar la aplicación en producción
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
