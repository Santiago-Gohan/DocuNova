# DocuNova

Sistema para organizar documentos de estudiantes: clasifica por tipo con **OCR local en español**, crea estructuras de carpetas, normaliza nombres y separa PDFs grandes. Incluye **versión web** (Flask) con **usuarios**, **roles (admin/usuario)** y **carpeta privada por usuario**.

Todo el procesamiento ocurre en el equipo donde corre: los documentos no se envían a servicios externos.

## Funciones

**Versión web** (`webapp/app.py`)
- Registro/login con contraseñas cifradas (hash). El **primer usuario es admin**.
- Panel de administrador: ver, crear, eliminar usuarios, cambiar rol, activar/desactivar, resetear contraseña y ver actividad.
- **Carpeta privada por usuario**: cada quien sube y gestiona SUS documentos; nadie más los ve (el admin sí).
- Herramientas: convertir texto, crear estructura, normalizar, **clasificar** (detecta el tipo) y **separar un PDF grande**.

**App de escritorio** (`organizador.py`)
- Interfaz Tkinter con 5 pestañas (convertir, crear, normalizar, clasificar, separar PDF).
- `analizar_grande.py`: radiografía de un PDF por páginas (CLI).

## Tipos de documento que detecta

| N.º | Documento | Cuándo |
|-----|-----------|--------|
| 001 | Acta de compromiso | Todos |
| 002 | Documento de identidad (cédula/TI) | Todos |
| 003 | Certificado académico | Todos |
| 004 | Certificado EPS | Todos |
| 005 | Tratamiento de datos | Solo menores |
| 006 | Registro civil | Solo menores |
| 007 | Documento del tutor legal | Solo menores |

## Instalación

```bash
pip install -r requirements.txt
python descargar_idioma.py
```

Para el OCR se necesita **Tesseract** instalado:
- Windows: `winget install -e --id UB-Mannheim.TesseractOCR`

## Uso

**Web** (doble clic en `INICIAR_WEB.bat` o):
```bash
cd webapp
python app.py
```
Abre `http://127.0.0.1:5000`. El primer usuario que se registre será **admin**.

**Escritorio**:
```bash
python organizador.py
```

## Despliegue

La app es Python/Flask: **no corre en GitHub Pages**. Para publicarla sin usar túneles, súbela a un host que ejecute Python (Render, Railway, Fly.io, PythonAnywhere). Recuerda instalar Tesseract y ejecutar `descargar_idioma.py` en el servidor.

## Estructura

```
webapp/
  app.py            servidor Flask
  db.py             usuarios, documentos y base de datos SQLite
  templates/        paginas HTML
  static/style.css  estilos
  datos/            carpetas privadas (no se sube al repo)
  trabajos/         archivos temporales por sesion
inteligencia.py     motor de lectura/OCR y clasificacion
organizador.py      app de escritorio
analizar_grande.py  analisis de PDF por paginas (CLI)
descargar_idioma.py descarga el idioma OCR (espanol)
```

## Aviso

Los documentos contienen datos personales. Al desplegar en un servidor de terceros, esos datos saldrían de tu equipo. Para máxima privacidad, córrelo en local.
