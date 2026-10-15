/* =====================================================================
   DocuNova - Interfaz: overlay de carga con barra de progreso.

   Se muestra al enviar formularios "pesados" (los que suben archivos o
   los marcados con  data-cargando). El OCR corre en el servidor, asi que
   la barra es una ESTIMACION visual de la espera.

   Personalizacion por formulario (atributos opcionales):
     data-titulo="..."   texto grande
     data-sub="..."      texto pequeno
     data-cargando       fuerza mostrar el overlay aunque no suba archivo
   ===================================================================== */
(function () {
  "use strict";

  var overlay, bar, pct, titleEl, subEl, timer, valor = 0;

  function el(id) { return document.getElementById(id); }

  function pintar() {
    bar.style.width = valor + "%";
    pct.textContent = Math.round(valor) + "%";
    overlay.setAttribute("aria-valuenow", String(Math.round(valor)));
  }

  function mostrar(titulo, subtitulo) {
    if (!overlay) { return; }
    if (titulo) { titleEl.textContent = titulo; }
    if (subtitulo) { subEl.textContent = subtitulo; }
    overlay.style.display = "flex";

    /* La barra sube rapido al inicio y se frena acercandose al 92% */
    valor = 4;
    pintar();
    window.clearInterval(timer);
    timer = window.setInterval(function () {
      var paso = valor < 30 ? 7 : valor < 60 ? 4 : valor < 80 ? 2 : 1;
      valor = Math.min(92, valor + paso);
      pintar();
    }, 450);
  }

  function ocultar() {
    if (overlay) { overlay.style.display = "none"; }
    window.clearInterval(timer);
  }

  function iniciar() {
    overlay = el("loading-overlay");
    if (!overlay) { return; }
    bar = el("progress-bar");
    pct = el("progress-pct");
    titleEl = el("loading-title");
    subEl = el("loading-subtitle");

    var forms = document.querySelectorAll("form");
    for (var i = 0; i < forms.length; i++) {
      var f = forms[i];
      /* Solo formularios que suben archivos o los marcados a mano */
      var pesado = f.hasAttribute("data-cargando") || f.querySelector('input[type="file"]');
      if (!pesado) { continue; }
      f.addEventListener("submit", function () {
        mostrar(this.getAttribute("data-titulo"),
                this.getAttribute("data-sub"));
      });
    }

    /* Si el navegador restaura la pagina (atras/adelante), oculta el overlay */
    window.addEventListener("pageshow", ocultar);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
