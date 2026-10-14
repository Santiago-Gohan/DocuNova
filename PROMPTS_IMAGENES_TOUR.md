# Prompts para generar las imágenes del tour de DocuNova

El recorrido ya está **programado** en la app (bocadillo, "n de N", botones
Siguiente/Atrás/Finalizar y barra de progreso). Solo faltan las **imágenes** de los
personajes. No soy un generador de imágenes, así que aquí tienes los prompts listos
para pegarlos en la herramienta que uses (Midjourney, DALL·E, Leonardo, Stable
Diffusion, etc.).

## Cómo integrarlas
1. Genera cada imagen con su prompt.
2. Guárdala como PNG y renómbrala con el nombre indicado (ej. `1_goku.png`).
3. Ponlas en: `webapp/static/tour/`
4. Listo: el tour las tomará automáticamente. Si una falta, muestra un emoji.

---

## Bloque de estilo común (pégalo al inicio de cada prompt)
> A clean, modern flat-design onboarding illustration in the style of a SaaS product
> tour. High-quality anime cel-shaded art faithful to Dragon Ball Z, vibrant saturated
> colors, crisp lineart, subtle rim light. The character stands full-body on the LEFT
> side, looking at the viewer with a friendly, encouraging expression, floating slightly.
> On the RIGHT, a minimal flat white speech bubble / tooltip with a thin accent border and
> a modern sans-serif UI font. Inside the bubble: a bold title and one line of Spanish
> instruction text (see text per step), plus small discreet step controls reading
> "N de 11" and a rounded "Siguiente" (or "Finalizar" on the last) pill button, and a row
> of tiny progress dots. Background: soft blurred tech gradient (deep blue to cyan) with
> subtle Dragon Ball mountain silhouettes and a faint glowing star; do not distract from
> the character. Vertical composition, 3:4, transparent-friendly, no watermark, no logos.

Reemplaza en cada paso: el personaje, la actitud, el texto del bocadillo y el control
de paso. Usa `--ar 3:4` en Midjourney.

---

## Paso 1 — Goku
**Archivo:** `1_goku.png`
**Texto del bocadillo:** "¡Hola! ¡Soy Goku! ¡Bienvenido a tu nueva cuenta! Pulsa 'Siguiente' para empezar."
**Control:** "1 de 11" + botón **Siguiente**
**Prompt:** *(estilo común)* + Son Goku in his orange and blue gi, spiky black hair, big warm smile, giving a thumbs up and a small wave with the other hand. Energetic welcoming pose.

## Paso 2 — Vegeta
**Archivo:** `2_vegeta.png`
**Texto del bocadillo:** "¡Hmph! ¡No hay tiempo que perder! Inicia sesión y completa tu perfil primero."
**Control:** "2 de 11" + botón **Siguiente**
**Prompt:** *(estilo común)* + Vegeta in his blue Saiyan armor, arms crossed, confident smirk, one eyebrow raised, authoritative stance. Proud and demanding but friendly.

## Paso 3 — Bulma
**Archivo:** `3_bulma.png`
**Texto del bocadillo:** "¡Hola, soy Bulma! Sube tus documentos y el sistema detecta el tipo solo. ¡Solo tú los ves!"
**Control:** "3 de 11" + botón **Siguiente**
**Prompt:** *(estilo común)* + Bulma with short blue hair, wearing a lab coat over a bright outfit, holding a tablet, cheerful and tech-savvy expression, mid-explanation gesture.

## Paso 4 — Piccolo
**Archivo:** `4_piccolo.png`
**Texto del bocadillo:** "¡Concéntrate! Escribe un nombre por línea y elige MAYÚSCULAS, minúsculas o Tipo Título."
**Control:** "4 de 11" + botón **Siguiente**
**Prompt:** *(estilo común)* + Piccolo, green Namekian with a serious focused face, arms crossed, meditative yet instructive posture. Calm, disciplined mentor energy.

## Paso 5 — Gohan
**Archivo:** `5_gohan.png`
**Texto del bocadillo:** "Soy Gohan. Escribe los estudiantes (Nombre, Número, S/N) y te genero un ZIP con sus carpetas."
**Control:** "5 de 11" + botón **Siguiente**
**Prompt:** *(estilo común)* + Gohan (teen/young adult) with black hair and glasses, scholarly look, holding a folder or clipboard, friendly and helpful smile.

## Paso 6 — Trunks
**Archivo:** `6_trunks.png`
**Texto del bocadillo:** "¡Rápido y preciso! Sube varios archivos y los clasifico y renombro por ti."
**Control:** "6 de 11" + botón **Siguiente**
**Prompt:** *(estilo común)* + Trunks (Future Trunks) with lavender hair and a Capsule Corp jacket, holding a sword at his side, confident cool expression, pointing at the bubble.

## Paso 7 — Krilin
**Archivo:** `7_krillin.png`
**Texto del bocadillo:** "¡Hey! ¿Un PDF con muchos documentos? Lo analizo y lo divido en documentos sueltos."
**Control:** "7 de 11" + botón **Siguiente**
**Prompt:** *(estilo común)* + Krillin, bald with six dots on his forehead, small stature, in his orange training gi, cheerful and encouraging, making a scissor/splitting hand gesture.

## Paso 8 — Chi-Chi
**Archivo:** `8_chichi.png`
**Texto del bocadillo:** "Tus datos están protegidos: el reconocimiento se hace aquí y no se envían a internet."
**Control:** "8 de 11" + botón **Siguiente**
**Prompt:** *(estilo común)* + Chi-Chi wearing her blue and red outfit with a helmet-like hairband, protective and caring expression, holding a small shield or padlock icon, maternal guardian vibe.

## Paso 9 — Goten
**Archivo:** `9_goten.png`
**Texto del bocadillo:** "¡No te asustes! La primera carga tarda un poquito porque el servicio despierta."
**Control:** "9 de 11" + botón **Siguiente**
**Prompt:** *(estilo común)* + Goten (kid) with black spiky hair, small and adorable, giving a reassuring cheerful smile, small sparkles around him.

## Paso 10 — Videl
**Archivo:** `10_videl.png`
**Texto del bocadillo:** "Soy Videl. Cambia tu contraseña desde 'Mi perfil'. Y si eres admin, gestiona usuarios."
**Control:** "10 de 11" + botón **Siguiente**
**Prompt:** *(estilo común)* + Videl with her signature pigtails and white shirt with orange accents, confident friendly smile, gesturing toward the bubble. Capable and modern.

## Paso 11 — Shenron
**Archivo:** `11_shenron.png`
**Texto del bocadillo:** "¡Has reunido las siete esferas! ¡Ya conoces DocuNova, ve y úsalo con todo tu poder!"
**Control:** "11 de 11" + botón **Finalizar**
**Prompt:** *(estilo común)* + Shenron, the giant green Chinese-style dragon, coiling majestically, glowing red eyes, golden horns, magical aura, looking wise and celebratory. Behind him, seven glowing Dragon Balls faintly visible in the background.

---

## Consejo
Para que todos se vean del mismo estilo, genera primero el **Paso 1 (Goku)** y, si tu
herramienta lo permite, usa esa imagen como **referencia de estilo** (`--sref` en
Midjourney o *image prompt*) para los demás. Mantén el mismo fondo y la misma posición
de la burbuja para que la transición entre pasos se sienta consistente.

## ¿Y si no quiero generar imágenes?
El tour ya funciona sin ellas: cada paso muestra un emoji representativo
(🥋 Goku, 💪 Vegeta, 🔧 Bulma, 🧘 Piccolo, 📚 Gohan, ⚔️ Trunks, ☀️ Krilin,
🛡️ Chi-Chi, ✨ Goten, 🎯 Videl, 🐉 Shenron).
