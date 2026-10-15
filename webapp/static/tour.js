/* =====================================================================
   DocuNova - "Product Tour" flotante (modal con personaje independiente)

   - El PERSONAJE se carga aparte en <img id="tour-character-img">.
   - El TEXTO vive en HTML real (#tour-title, #tour-text), NUNCA dentro
     de la imagen.
   - Edita el arreglo PASOS para cambiar textos, personajes o el numero
     de pasos (1..10). El contador y los puntos se calculan solos.

   Imagenes: se buscan en  webapp/static/assets/characters/  con el nombre
   "<id>.png". Si no existe se prueba .jpg/.jpeg/.webp y, si nada aparece,
   se muestra el emoji del personaje (nunca una imagen rota).

   API publica:  window.abrirTour()
   ===================================================================== */
(function () {
  "use strict";

  /* -------------------------------------------------------------------
     1) CONFIGURACION
     ------------------------------------------------------------------- */

  /* Pregunta inicial (primera vez que entra un usuario logueado). */
  var INTRO = {
    id: "goku", emoji: "\uD83E\uDD4B", color: "#f97316",
    quien: "Goku", titulo: "\u00a1Hola! Soy Goku",
    texto: "\u00bfYa dominas las t\u00e9cnicas de este sistema o necesitas " +
           "que te entrene desde cero con esta gu\u00eda interactiva?"
  };

  /* -------------------------------------------------------------------
     PASOS (edita SOLO este arreglo)
     id     -> nombre del archivo de imagen sin extension (ej: "goku")
     emoji  -> respaldo si falta la imagen
     color  -> color de la etiqueta del personaje
     quien  -> nombre en la etiqueta
     titulo -> titulo del paso
     texto  -> explicacion (HTML real)
     btn    -> texto del boton principal (por defecto "Siguiente")
     ------------------------------------------------------------------- */
  var PASOS = [
    { id: "goku", emoji: "\uD83E\uDD4B", color: "#f97316", quien: "Goku",
      titulo: "Bienvenida",
      texto: "\u00a1Hola! Soy Goku. Entra a tu 'Perfil' para empezar tu entrenamiento.",
      btn: "Siguiente" },
    { id: "vegeta", emoji: "\uD83D\uDCAA", color: "#2563eb", quien: "Vegeta",
      titulo: "Estad\u00edsticas",
      texto: "No pierdas tiempo, insecto. Ve al 'Dashboard' y revisa tus estad\u00edsticas.",
      btn: "Entendido" },
    { id: "bulma", emoji: "\uD83D\uDD27", color: "#0d9488", quien: "Bulma",
      titulo: "Herramientas",
      texto: "\u00a1Genial! A\u00f1ad\u00ed nuevas funciones. Pru\u00e9balas en 'Herramientas'.",
      btn: "Ver m\u00e1s" },
    { id: "krillin", emoji: "\uD83D\uDC51", color: "#ca8a04", quien: "Krillin",
      titulo: "Clasifica tus documentos",
      texto: "Con OCR local leemos tus PDFs. Ordena todo desde 'Clasificar' y 'Separar'.",
      btn: "Siguiente" },
    { id: "gohan", emoji: "\uD83D\uDCD8", color: "#16a34a", quien: "Gohan",
      titulo: "Crea tu estructura",
      texto: "Usa 'Crear' y 'Convertir' para generar la carpeta numerada 001..007.",
      btn: "Siguiente" },
    { id: "personaje6", emoji: "\uD83D\uDC09", color: "#b45309", quien: "Shenron",
      titulo: "Cierre del tour",
      texto: "\u00a1Felicidades! Completaste el entrenamiento. Ahora ve y usa tu poder.",
      btn: "Terminar" }

    /* Para llegar a 10 pasos: agrega mas bloques { ... } aqui, con su PNG
       en assets/characters/ (ej: "piccolo", "trunks", "chichi", "roshi"). */
  ];

  var CLAVE_VISTO = "docunova_tour_v3";
  var EXTENSIONES = ["png", "jpg", "jpeg", "webp"];

  /* -------------------------------------------------------------------
     2) ESTADO Y REFERENCIAS AL DOM
     ------------------------------------------------------------------- */
  var raiz, img, emoji, badge, titulo, texto;
  var cajaIntro, cajaPasos, btnNext, btnPrev, puntos;
  var enIntro = true, idx = 0;

  function el(id) { return document.getElementById(id); }

  /* -------------------------------------------------------------------
     3) PINTAR EL PERSONAJE + TEXTOS DE UN PASO
     ------------------------------------------------------------------- */
  function pintarPersonaje(p) {
    var base = raiz.getAttribute("data-imgbase") || "/static/assets/characters/";

    /* Intenta <base><id>.png; si falla prueba .jpg/.jpeg/.webp y al final emoji */
    var n = 0;
    img.onerror = function () {
      n++;
      if (n >= EXTENSIONES.length) {        /* se agotaron: usar emoji */
        img.style.display = "none";
        emoji.style.display = "block";
      } else {
        img.src = base + p.id + "." + EXTENSIONES[n];
      }
    };
    img.style.display = "";
    emoji.style.display = "none";
    img.src = base + p.id + "." + EXTENSIONES[0];
    img.alt = p.quien;
    emoji.textContent = p.emoji;

    badge.textContent = p.quien;
    badge.style.background = p.color;
    titulo.textContent = p.titulo;   /* texto HTML real */
    texto.textContent = p.texto;
  }

  /* -------------------------------------------------------------------
     4) PINTAR LA VISTA COMPLETA (intro o paso)
     ------------------------------------------------------------------- */
  function pintar() {
    if (enIntro) {
      pintarPersonaje(INTRO);
      cajaIntro.style.display = "flex";
      cajaPasos.style.display = "none";
      puntos.innerHTML = "";
      return;
    }
    var p = PASOS[idx];
    pintarPersonaje(p);
    btnPrev.style.visibility = idx === 0 ? "hidden" : "visible";
    btnNext.textContent = p.btn || "Siguiente";
    var html = "";
    for (var k = 0; k < PASOS.length; k++) {
      html += '<i class="' + (k === idx ? "on" : "") + '"></i>';
    }
    puntos.innerHTML = html;
    cajaIntro.style.display = "none";
    cajaPasos.style.display = "flex";
  }

  /* -------------------------------------------------------------------
     5) ACCIONES: abrir / avanzar / retroceder / cerrar
     ------------------------------------------------------------------- */
  function abrir() {
    enIntro = true; idx = 0;
    raiz.hidden = false;
    raiz.classList.remove("abierto");
    void raiz.offsetWidth;               /* reflow para reanimar */
    raiz.classList.add("abierto");
    pintar();
  }
  function avanzar() {
    if (enIntro) { enIntro = false; idx = 0; pintar(); return; }
    if (idx >= PASOS.length - 1) { cerrar(); return; }
    idx++; pintar();
  }
  function retroceder() {
    if (enIntro || idx === 0) { return; }
    idx--; pintar();
  }
  function cerrar() {
    raiz.classList.remove("abierto");
    try { localStorage.setItem(CLAVE_VISTO, "1"); } catch (e) {}
    raiz.hidden = true;
  }

  /* -------------------------------------------------------------------
     6) INICIALIZACION
     ------------------------------------------------------------------- */
  function iniciar() {
    raiz = el("tour-modal");
    if (!raiz) { return; }               /* no hay tour en esta pagina */

    img = el("tour-character-img");
    emoji = el("tour-emoji");
    badge = el("tour-badge");
    titulo = el("tour-title");
    texto = el("tour-text");
    cajaIntro = el("tour-intro");
    cajaPasos = el("tour-steps");
    btnNext = el("btn-next");
    btnPrev = el("btn-prev");
    puntos = el("tour-dots");

    btnNext.addEventListener("click", avanzar);
    btnPrev.addEventListener("click", retroceder);
    el("tour-close").addEventListener("click", cerrar);
    el("btn-expert").addEventListener("click", cerrar);
    el("btn-teach").addEventListener("click", function () {
      enIntro = false; idx = 0; pintar();
    });

    document.addEventListener("keydown", function (ev) {
      if (raiz.hidden) { return; }
      if (ev.key === "Escape") { cerrar(); }
      if (enIntro) { return; }
      if (ev.key === "ArrowRight") { avanzar(); }
      if (ev.key === "ArrowLeft") { retroceder(); }
    });

    window.abrirTour = abrir;

    var visto = false;
    try { visto = localStorage.getItem(CLAVE_VISTO) === "1"; } catch (e) {}
    if (!visto) { window.setTimeout(abrir, 700); }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
