# DocuNova

**Sistema web para organizar los documentos de tus estudiantes** — clasifica cada
archivo por tipo con **OCR local en español**, detecta a quién pertenece (nombre,
tipo y número de documento), arma la carpeta de cada persona, normaliza nombres y
separa PDFs grandes.

> Demo en vivo: **https://docunova-v7za.onrender.com**

Todo el procesamiento ocurre en el equipo/servidor donde corre la app: los
documentos **no se envían a servicios externos**.

---

## ¿Qué hace?

Subes una carpeta (o un ZIP) con los documentos de varios estudiantes y DocuNova:

1. **Lee** cada archivo (capa de texto del PDF o OCR si está escaneado).
2. **Detecta a la persona**: nombre, tipo de documento (CC/TI/CE/RC/PP/NIT) y número.
3. **Clasifica el documento** en la nomenclatura 001–007.
4. **Crea una carpeta por persona** con sus documentos ya clasificados.

Ejemplo de resultado:

```
SANTIAGO_BARRERA_BARBOSA_CC_1031649321/
  001_ACTA_DE_COMPROMISO.pdf
  002_DOCUMENTO_DE_IDENTIDAD.pdf
  003_CERTIFICADO_ACADEMICO.pdf
  004_CERTIFICADO_EPS.pdf
```

## Funciones

**Versión web** (`webapp/app.py`)
- Registro/login con contraseñas cifradas (hash). El **primer usuario es admin**.
- Sesión con cierre por inactividad (30 min) o al cerrar el navegador.
- Panel de administrador: ver, crear, eliminar usuarios, cambiar rol,
  activar/desactivar, resetear contraseña y ver la actividad.
- **Carpeta privada por usuario**: cada quien gestiona SUS documentos.
- Herramientas:
  - **Convertir** texto y **Estructura** (crea el árbol de carpetas).
  - **Clasificar** varios documentos y descargar el ZIP.
  - **Separar PDF** grande por tipo de documento.
  - **Organizar por persona**: detecta personas y crea una carpeta por cada una.
  - **Normalizar** nombres.
- Tema oscuro, barra de progreso al procesar y **tour guiado** flotante.
- **Trabajos en segundo plano con progreso real** (`webapp/trabajos.py`): el OCR corre en
  un hilo aparte y el navegador consulta `/trabajo/<id>`, así el servidor nunca corta la
  petición por tiempo y la barra muestra el avance real (*"Analizando página 12 de 50"*),
  con cola de un proceso a la vez y botón de reintento si algo falla.

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

## Tecnologías

Python 3.12 · Flask · PyMuPDF · Tesseract OCR (español) · SQLite/PostgreSQL (Neon) ·
Docker · Render.

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

La app es Python/Flask: **no corre en GitHub Pages**. El repo incluye `Dockerfile`,
`Procfile` y `render.yaml`, que instalan Tesseract y el idioma OCR automáticamente.

Guía paso a paso: ver **[DESPLIEGUE.md](DESPLIEGUE.md)** (Render/Railway).

## Estructura

```
webapp/
  app.py            servidor Flask
  db.py             usuarios, documentos y base de datos (SQLite/PostgreSQL)
  templates/        paginas HTML
  static/style.css  estilos (tema oscuro)
  static/ui.js      overlay de carga y barra de progreso
  static/tour.js    tour guiado flotante
  datos/            carpetas privadas (no se sube al repo)
  trabajos/         archivos temporales por sesion
nomenclatura.py     logica de nombres (compartida web/escritorio)
inteligencia.py     motor de lectura/OCR y clasificacion
organizador.py      app de escritorio
analizar_grande.py  analisis de PDF por paginas (CLI)
descargar_idioma.py descarga el idioma OCR (espanol)
Dockerfile          imagen para desplegar (instala Tesseract + espanol)
render.yaml         configuracion de despliegue en Render
```

## Aviso

Los documentos contienen datos personales. Al desplegar en un servidor de terceros,
esos datos saldrían de tu equipo. Para máxima privacidad, córrelo en local.

---

Hecho en Colombia 💙 SENA ADSO
