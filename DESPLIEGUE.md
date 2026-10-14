# Despliegue de DocuNova (sin túneles)

El código ya está en GitHub: **https://github.com/Santiago-Gohan/DocuNova**

Como DocuNova es una app **Python/Flask**, GitHub por sí solo **no la ejecuta**.
Hay que publicarla en un servicio que ejecute Python. Aquí la receta con **Render**
(gratis) usando el `Dockerfile` que ya trae el repo (que además instala Tesseract
y el idioma español del OCR automáticamente).

---

## Opción recomendada: Render (gratis)

1. Crea una cuenta en https://render.com (puedes entrar con tu GitHub).
2. En el panel: **New +** → **Web Service**.
3. Conecta tu repositorio **DocuNova**.
4. Render detecta el `Dockerfile` solo. Verifica:
   - **Runtime / Environment:** Docker
   - **Instance Type:** Free
5. Agrega estas **Environment Variables** (si no usaste el Blueprint):
   - `ENTORNO` = `produccion`
   - `ORGANIZADOR_CLAVE` = *(cualquier texto largo y secreto)*
6. Clic en **Create Web Service** y espera a que termine el build.
7. Te dará un enlace tipo: `https://docunova.onrender.com`
8. Ábrelo, regístrate: **el primer usuario será el administrador**.

> También puedes usar el **Blueprint**: en Render, **New +** → **Blueprint** →
> elige el repo. Render leerá el `render.yaml` y configurará todo automáticamente.

### ⚠️ Importante en el plan gratis de Render
- El servicio **se duerme** tras unos minutos sin uso; la primera visita tarda ~30-60 s en despertar.
- El **almacenamiento es temporal**: la base de datos de usuarios y los documentos
  **se borran** en cada nuevo despliegue o reinicio.

### Para conservar datos (opcional, plan de pago)
1. En Render, agrega un **Disk** montado en `/data`.
2. Define estas variables de entorno:
   - `ORGANIZADOR_DB` = `/data/organizador.db`
   - `ORGANIZADOR_DATOS` = `/data/datos`
   - `ORGANIZADOR_TRABAJOS` = `/data/trabajos`

---

## Alternativa: Railway

1. Crea cuenta en https://railway.app (con GitHub).
2. **New Project → Deploy from GitHub repo → DocuNova**.
3. Railway detecta el `Dockerfile`. Agrega las mismas variables:
   - `ENTORNO` = `produccion`
   - `ORGANIZADOR_CLAVE` = *(secreto largo)*
4. En **Settings → Networking**, genera un dominio público.
5. Para persistencia, agrega un **Volume** montado en `/data` y las 3 variables de rutas.

---

## Variables de entorno

| Variable | Para qué | Ejemplo |
|----------|----------|---------|
| `ENTORNO` | Activa modo producción (desactiva "Mi PC") | `produccion` |
| `ORGANIZADOR_CLAVE` | Clave de sesiones (seguridad) | texto largo aleatorio |
| `PORT` | Puerto (lo pone el host solo) | `10000` |
| `ORGANIZADOR_DB` | Ruta de la base de datos | `/data/organizador.db` |
| `ORGANIZADOR_DATOS` | Carpeta de documentos privados | `/data/datos` |
| `ORGANIZADOR_TRABAJOS` | Carpeta de trabajos temporales | `/data/trabajos` |
| `TESSERACT_CMD` | Ruta del binario de Tesseract (si es distinta) | `/usr/bin/tesseract` |

---

## Sobre el OCR
El idioma español (`spa.traineddata`, 13 MB) **no** está en el repositorio a propósito
(es un binario pesado). Se resuelve **automáticamente**:
- El `Dockerfile` ejecuta `python descargar_idioma.py` durante el build.
- Si faltara al arrancar, la app intenta descargarlo sola.

En tu PC (Windows) sigue funcionando con el Tesseract instalado localmente.
