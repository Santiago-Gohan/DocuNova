# Manual de uso de DocuNova

**Sitio:** https://docunova-v7za.onrender.com
**Qué es:** un gestor de documentos para colegios/instituciones. Organiza, renombra,
clasifica y separa documentos de estudiantes de forma automática. El reconocimiento
de texto (OCR) corre **en el servidor** y **no se envían documentos a servicios externos**.

---

## 1. Crear la cuenta

1. Abre el enlace y entra a **Registrarse**.
2. Llena:
   - **Nombre completo** (ej.: `Santiago Barrera`)
   - **Usuario** (3 a 30 caracteres; letras, números, `.`, `_`, `-`)
   - **Correo**
   - **Contraseña** (mínimo 6 caracteres) y repítela.
3. Clic en **Crear cuenta**.

> **Importante:** el **primer usuario** que se registre queda como **administrador**.
> Los siguientes quedan como usuarios normales (el admin puede cambiarles el rol).

Luego entras con **Usuario o correo** + **Contraseña**.

---

## 2. Roles

| Rol | Puede hacer |
|-----|-------------|
| **usuario** | Usar todas las herramientas y su carpeta privada de documentos. |
| **admin** | Todo lo anterior **+** panel de Administración, gestionar usuarios y (solo en tu PC) explorar "Mi PC". |

---

## 3. Las herramientas (menú superior)

### 3.1 Inicio
Muestra los accesos rápidos y el **estado del sistema** (si la lectura OCR en español está activa).

### 3.2 Mis documentos
Tu **carpeta privada** (solo tú la ves):
- **Subir:** elige uno o varios PDF/imágenes → al subirlos se **detecta el tipo automáticamente**.
- **Descargar** cada archivo.
- **Borrar** un archivo (pide confirmación).
- Muestra **tipo detectado**, **confianza**, **tamaño** y **fecha**.

### 3.3 Convertir texto
Escribe un nombre por línea y obtén el resultado en los **3 formatos** a la vez:
- **MAYÚSCULAS** → `SANTIAGO BARRERA`
- **minúsculas** → `santiago barrera`
- **Tipo Título** → `Santiago Barrera` (mantiene siglas como `CC`, `TI`, `EPS`, `PDF` en mayúscula).

### 3.4 Crear estructura
Genera un **ZIP** con una carpeta por estudiante y sus documentos ya nombrados.

- **Formato de entrada** (una línea por estudiante):
  ```
  Nombre Apellido, NúmeroDeDocumento, S
  ```
  - `S` = es **menor de edad** → agrega también los documentos 005, 006 y 007.
  - `N` = no es menor.
  - Ejemplo:
    ```
    Santiago Barrera, 1031649321, N
    Juan Perez, 1020304050, S
    ```
- Elige el **formato de nombres** y descarga el ZIP.
- La carpeta del estudiante queda así: `SANTIAGO_BARRERA_CC_1031649321`

### 3.5 Clasificar documentos
Sube uno o varios **PDF o imágenes** (puedes seleccionar varios). El sistema:
1. Lee el documento (OCR si está escaneado).
2. **Detecta el tipo** (Acta, Cédula, Certificado académico, etc.).
3. Lo **renombra** con la nomenclatura correcta.
4. Ofrece un **ZIP** con todos los documentos ya renombrados.

La tabla de resultados muestra: archivo subido, tipo detectado, confianza y nuevo nombre.

### 3.6 Separar PDF grande
Para un **único PDF** que contiene **varios documentos** (por ejemplo, todas las
cédulas del curso escaneadas juntas):

1. Sube el PDF → **Analizar páginas** (si está escaneado, tarda: aplica OCR página por página).
2. Revisa el **resumen**, los **cortes detectados** y el **detalle por página**.
3. Elige el formato y **Separar y descargar ZIP** → un archivo por documento.

> Si dos páginas pertenecen al mismo documento (p. ej. cédula al frente y al reverso),
> el sistema las une en un solo archivo.

---

## 4. Nomenclatura de documentos

Los documentos se numeran en este orden:

| N.º | Documento | ¿Cuándo? |
|-----|-----------|----------|
| 001 | ACTA DE COMPROMISO | todos |
| 002 | DOCUMENTO DE IDENTIDAD | todos |
| 003 | CERTIFICADO ACADEMICO | todos |
| 004 | CERTIFICADO EPS | todos |
| 005 | TRATAMIENTO DE DATOS | solo menores |
| 006 | REGISTRO CIVIL | solo menores |
| 007 | DOCUMENTO TUTOR LEGAL | solo menores |

Tipos de documento reconocidos: **CC, TI, CE, PP, RC, NIT**.

---

## 5. Mi perfil
- Cambiar **nombre** y **correo**.
- Cambiar **contraseña** (pide la actual).

---

## 6. Panel de administrador (solo admin)

- **Ver usuarios** con rol, estado, último acceso.
- **Crear usuario** (con rol).
- **Hacer/Quitar admin**, **Activar/Desactivar**, **Resetear contraseña**.
- **Eliminar** usuario (no puedes eliminarte a ti mismo ni dejar el sistema sin admins).
- **Documentos:** ver la carpeta privada de cada usuario.
- **Actividad reciente:** registro de acciones.

---

## 7. Preguntas frecuentes

**La página tarda en abrir la primera vez.**
Es normal: el servicio gratuito "duerme" sin uso y despierta en 30-60 s.

**¿A dónde van mis documentos?**
Al servidor de la aplicación. No se comparten con terceros ni servicios de OCR externos.

**No detectó bien un documento.**
Puede pasar con escaneos borrosos o girados. Prueba subir una imagen más nítida;
el "tipo detectado" muestra un porcentaje de **confianza**.

**Olvidé mi contraseña.**
Pídele al **administrador** que la resetee desde el panel.

**¿Hay app de escritorio?**
Sí, existe una versión local (Windows) con las mismas herramientas.
