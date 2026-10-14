FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ENTORNO=produccion \
    PORT=5000

# Tesseract (OCR) + idiomas base
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt gunicorn

COPY . .

# Descarga el idioma español del OCR dentro de la imagen
RUN python descargar_idioma.py

EXPOSE 5000

CMD gunicorn --chdir webapp -k gthread -w 1 --threads 8 -t 300 -b 0.0.0.0:${PORT} app:app
