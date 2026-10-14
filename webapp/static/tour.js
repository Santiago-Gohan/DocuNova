/* =====================================================================
   DocuNova - Tour guiado estilo "product tour" flotante.
   El personaje se superpone a la pagina real y la burbuja es un tooltip
   moderno. Las imagenes son opcionales (si no existen, se usa un emoji).
   Coloca tus PNG con fondo transparente en:  webapp/static/tour/
   ===================================================================== */
(function () {
  "use strict";

  /* Pregunta inicial (solo con la sesion iniciada) */
  var INTRO = {
    id: "0_goku", emoji: "\uD83E\uDD4B", color: "#f97316",
    quien: "Goku", titulo: "\u00a1Hola! Soy Goku",
    texto: "\u00bfYa dominas las t\u00e9cnicas de este sistema o necesitas que te entrene desde cero con esta gu\u00eda interactiva?"
  };

  /* Pasos de la guia. "btn" es el texto del boton principal de cada paso. */
  var PASOS = [
    {
      id: "1_goku", emoji: "\uD83E\uDD4B", color: "#f97316",
      quien: "Goku", titulo: "Bienvenida",
      texto: "\u00a1Hola! Soy Goku. Haz clic en 'Perfil' para empezar tu entrenamiento!",
      btn: "Siguiente"
    },
    {
      id: "2_vegeta", emoji: "\uD83D\uDCAA", color: "#2563eb",
      quien: "Vegeta", titulo: "Estad\u00edsticas",
      texto: "No pierdas tiempo. Ve a 'Dashboard' y revisa tus estad\u00edsticas, insecto!",
      btn: "Entendido"
    },
    {
      id: "3_bulma", emoji: "\uD83D\uDD27", color: "#0d9488",
      quien: "Bulma", titulo: "Herramientas",
      texto: "\u00a1Genial! He a\u00f1adido nuevas funciones. \u00a1Pr\u00f3balas en la pesta\u00f1a 'Herramientas'!",
      btn: "Ver m\u00e1s"
    },
    {
      id: "4_roshi", emoji: "\uD83D\uDC22", color: "#b45309",
      quien: "Maestro Roshi", titulo: "Cierre del tour",
      texto: "\u00a1Felicidades! \u00a1Has completado el tour! \u00a1Ahora ve y usa tu poder!",
      btn: "Terminar"
    }
  ];

  var CLAVE = "docunova_tour_v3";
  var intro = true;   /* true = mostrando la pregunta inicial */
  var i = 0;          /* indice dentro de PASOS */
  var img, emoji, quien, titulo, texto, contador, btnSig, btnAtras, puntos, raiz;
  var nav, introBox;

  function el(id) { return document.getElementById(id); }

  function pintarBurbuja(p) {
    var base = raiz.getAttribute("data-imgbase") || "/static/tour/";
    img.onerror = function () { img.style.display = "none"; emoji.style.display = "block"; };
    img.style.display = "";
    emoji.style.display = "none";
    img.src = base + p.id + ".png";
    img.alt = p.quien;
    emoji.textContent = p.emoji;
    quien.textContent = p.quien;
    quien.style.background = p.color;
    titulo.textContent = p.titulo;
    texto.textContent = p.texto;
  }

  function pintar() {
    if (intro) {
      pintarBurbuja(INTRO);
      contador.textContent = "";
      puntos.style.display = "none";
      nav.style.display = "none";
      introBox.style.display = "flex";
      return;
    }
    var p = PASOS[i];
    pintarBurbuja(p);
    contador.textContent = (i + 1) + " de " + PASOS.length;
    btnAtras.style.visibility = i === 0 ? "hidden" : "visible";
    btnSig.textContent = p.btn;
    var html = "";
    for (var k = 0; k < PASOS.length; k++) {
      html += '<i class="' + (k === i ? "on" : "") + '"></i>';
    }
    puntos.innerHTML = html;
    puntos.style.display = "flex";
    nav.style.display = "flex";
    introBox.style.display = "none";
  }

  function abrir() {
    intro = true;
    i = 0;
    raiz.hidden = false;
    void raiz.offsetWidth;
    raiz.classList.add("abierto");
    pintar();
  }

  function cerrar() {
    raiz.classList.remove("abierto");
    try { localStorage.setItem(CLAVE, "1"); } catch (e) {}
    window.setTimeout(function () { raiz.hidden = true; }, 300);
  }

  function empezarEntrenamiento() {
    intro = false;
    i = 0;
    pintar();
  }

  function ir(n) {
    if (n < 0) { n = 0; }
    if (n >= PASOS.length) { cerrar(); return; }
    i = n;
    pintar();
  }

  function iniciar() {
    raiz = el("tour");
    if (!raiz) { return; }
    img = el("tour-img");
    emoji = el("tour-emoji");
    quien = el("tour-quien");
    titulo = el("tour-titulo");
    texto = el("tour-texto");
    contador = el("tour-paso");
    btnSig = el("tour-sig");
    btnAtras = el("tour-atras");
    puntos = el("tour-puntos");
    nav = el("tour-nav");
    introBox = el("tour-intro");

    btnSig.addEventListener("click", function () { ir(i + 1); });
    btnAtras.addEventListener("click", function () { ir(i - 1); });
    el("tour-cerrar").addEventListener("click", cerrar);
    el("tour-experto").addEventListener("click", cerrar);
    el("tour-maestro").addEventListener("click", empezarEntrenamiento);

    document.addEventListener("keydown", function (ev) {
      if (raiz.hidden) { return; }
      if (ev.key === "Escape") { cerrar(); }
      if (intro) { return; }
      if (ev.key === "ArrowRight") { ir(i + 1); }
      if (ev.key === "ArrowLeft") { ir(i - 1); }
    });

    window.abrirTour = function () { abrir(); };

    var visto = false;
    try { visto = localStorage.getItem(CLAVE) === "1"; } catch (e) {}
    if (!visto) {
      window.setTimeout(abrir, 700);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
