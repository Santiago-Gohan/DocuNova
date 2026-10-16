FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ENTORNO=produccion \
    PORT=5000 \
    DOCUNOVA_OCR_WORKERS=2

# Tesseract (OCR) + idioma espanol del sistema (no depende de descargar de GitHub)
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt gunicorn

COPY . .

# Descarga el idioma español del OCR dentro de la imagen (respaldo si el
# paquete del sistema no lo trae). Luego verifica que el OCR quede listo.
RUN python descargar_idioma.py || true
RUN python -c "import sys; sys.path.insert(0,'.'); import inteligencia as i; e=i.ocr_estado(); print('OCR', e); assert e['binario'] and e['spa'], 'OCR no disponible: falta Tesseract o spa.traineddata'"

EXPOSE 5000

CMD gunicorn --chdir webapp -k gthread -w 1 --threads 8 -t 300 -b 0.0.0.0:${PORT} app:app
