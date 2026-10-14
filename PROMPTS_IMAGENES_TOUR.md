# Prompts para generar las imágenes del tour de DocuNova

El recorrido ya está **programado** en la app (burbuja flotante, "n de N",
botones Siguiente/Entendido/Ver más/Terminar). Solo faltan las **imágenes** de los
personajes. No puedo generarlas yo, así que aquí van los prompts listos para pegar
en la herramienta que uses (Midjourney, DALL·E, Leonardo, Stable Diffusion, etc.).

## Cómo integrarlas
1. Genera cada imagen con su prompt.
2. Guárdala como PNG **con fondo transparente** y renómbrala con el nombre indicado.
3. Ponlas en: `webapp/static/tour/`
4. Listo: el tour las muestra como personaje flotante. Si falta una, usa un emoji.

> **Nota legal:** los personajes de Dragon Ball son material con derechos de autor.
> Usa arte propio/licenciado si vas a publicar esto. Para uso local/educativo puedes
> recortar imágenes existentes, pero no las subas a un repositorio público.

---

## Bloque de estilo común (pégalo al inicio de cada prompt)
> A clean, modern flat-design onboarding illustration in the style of a SaaS product
> tour. High-quality anime cel-shaded art faithful to Dragon Ball Z, vibrant saturated
> colors, crisp lineart, subtle rim light. The character stands full-body, looking at
> the viewer with a friendly, encouraging expression, floating slightly. **Pure
> transparent background** (PNG, no scenery, no floor, no text). Vertical composition
> 3:4, centered character, room around the silhouette, cut-out ready. No watermark,
> no logos.

Reemplaza solo el personaje y la actitud. Usa `--ar 3:4` (Midjourney) y, si tu
herramienta lo permite, `--sref` con la primera imagen para mantener el mismo estilo.

---

## Paso 1 — Goku · `1_goku.png` · "Siguiente"
Son Goku in his orange and blue gi, spiky black hair, big warm smile, giving a small
wave. Energetic welcoming pose.

## Paso 2 — Vegeta · `2_vegeta.png` · "Entendido"
Vegeta in his blue Saiyan armor, arms crossed, confident smirk, one eyebrow raised.
Proud and demanding but not angry.

## Paso 3 — Bulma · `3_bulma.png` · "Ver más"
Bulma with short blue hair, wearing a lab coat over a bright outfit, holding a
Dragon Radar / tablet, cheerful and tech-savvy, mid-explanation gesture.

## Paso 4 — Maestro Roshi · `4_roshi.png` · "Terminar"
Master Roshi (Kame Sennin), bald with sunglasses and white beard, turtle-shell back,
waving with a proud, celebrating gesture. Wise and joyful.

---

## ¿Y si no quiero generar imágenes?
El tour funciona sin ellas: cada paso muestra un emoji
(🥋 Goku, 💪 Vegeta, 🔧 Bulma, 🐢 Maestro Roshi).
