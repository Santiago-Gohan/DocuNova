/* =====================================================================
   DocuNova - Interfaz: overlay de carga con barra de progreso.

   DOS MODOS

   1) Formularios con  data-async  (clasificar, separar, organizar):
        a. los archivos se suben con XMLHttpRequest  ->  % real de subida;
        b. el servidor lanza el trabajo en un hilo y devuelve su id;
        c. se consulta  GET /trabajo/<id>  cada 700 ms  ->  % real del OCR
           y el texto de la fase ("Analizando pagina 12 de 50");
        d. al terminar se recarga la pagina de resultados.
      Si algo falla (subida, conexion o trabajo muerto) se muestra el motivo
      y un boton para reintentar: la barra NUNCA se queda congelada.

   2) El resto de formularios pesados: la barra es una estimacion visual
      mientras el navegador espera la respuesta (son operaciones cortas).

   Atributos por formulario:
      data-async              modo real con progreso del servidor
      data-redirect           URL a la que ir cuando el trabajo termina
      data-titulo / data-sub  textos del overlay
      data-cargando           fuerza el overlay aunque no suba archivo
   ===================================================================== */
(function () {
  "use strict";

  var overlay, bar, pct, titleEl, subEl, faseEl, cajaError, btnReintentar;
  var timer = null;
  var valor = 0, objetivo = 0;
  var ultimoForm = null, ultimoTrabajo = null, ultimoRedirect = null;
  var fallo = null;          /* 'envio' | 'vigilar' */
  var fallosRed = 0;

  function el(id) { return document.getElementById(id); }

  function pintar() {
    bar.style.width = valor + "%";
    pct.textContent = Math.round(valor) + "%";
    overlay.setAttribute("aria-valuenow", String(Math.round(valor)));
  }

  /* La barra avanza suavemente hasta el objetivo (que sube el servidor) */
  function arrancarBarra() {
    window.clearInterval(timer);
    timer = window.setInterval(function () {
      if (valor >= objetivo) { return; }
      var paso = valor < 30 ? 7 : valor < 60 ? 4 : valor < 80 ? 2 : 1;
      valor = Math.min(objetivo, valor + paso);
      pintar();
    }, 400);
  }

  function mostrar(titulo, subtitulo, real) {
    if (!overlay) { return; }
    if (titulo) { titleEl.textContent = titulo; }
    if (subtitulo) { subEl.textContent = subtitulo; }
    if (faseEl) { faseEl.textContent = ""; }
    if (cajaError) { cajaError.style.display = "none"; cajaError.textContent = ""; }
    if (btnReintentar) { btnReintentar.style.display = "none"; }
    overlay.removeAttribute("data-error");
    overlay.style.display = "flex";
    valor = 4;
    objetivo = real ? 8 : 92;   /* sin servidor: tope visual del 92% */
    pintar();
    arrancarBarra();
  }

  function ocultar() {
    if (overlay) { overlay.style.display = "none"; }
    window.clearInterval(timer);
  }

  function fase(texto) {
    if (faseEl && texto) { faseEl.textContent = texto; }
  }

  function error_(mensaje) {
    window.clearInterval(timer);
    if (cajaError) {
      cajaError.textContent = mensaje;
      cajaError.style.display = "block";
    }
    if (btnReintentar) { btnReintentar.style.display = "inline-flex"; }
    if (faseEl) { faseEl.textContent = "Proceso detenido"; }
    if (subEl) { subEl.textContent = "Puedes reintentar o cerrar esta ventana."; }
    overlay.setAttribute("data-error", "1");
  }

  /* ---------------- modo real: subir y luego vigilar ---------------- */

  function enviar(form) {
    ultimoForm = form;
    ultimoRedirect = form.getAttribute("data-redirect") || null;
    fallo = "envio";
    mostrar(form.getAttribute("data-titulo"),
            form.getAttribute("data-sub"), true);

    var datos = new FormData(form);
    var req = new XMLHttpRequest();
    req.open("POST", form.getAttribute("action") || window.location.href, true);
    req.setRequestHeader("X-Trabajo", "1");

    req.upload.onprogress = function (e) {
      if (!e.lengthComputable) { return; }
      var p = e.loaded / e.total;
      objetivo = Math.max(objetivo, Math.round(8 + p * 22));  /* 8 -> 30 */
      pintar();
      fase("Subiendo archivos... " + Math.round(p * 100) + "%");
    };

    req.onload = function () {
      /* Casos frecuentes con un mensaje claro (no un "estado 302") */
      if (req.responseURL && req.responseURL.indexOf("/login") !== -1) {
        error_("Tu sesión expiró. Vuelve a iniciar sesión y repite la operación.");
        return;
      }
      if (req.status === 413) {
        error_("Los archivos son demasiado grandes (máximo 300 MB en total).");
        return;
      }
      var data = {};
      try { data = JSON.parse(req.responseText) || {}; } catch (e) { data = {}; }
      if (req.status >= 200 && req.status < 300 && data.trabajo) {
        ultimoTrabajo = data.trabajo;
        fallo = "vigilar";
        fallosRed = 0;
        fase("Archivos recibidos. Preparando el trabajo...");
        vigilar(data.trabajo, ultimoRedirect);
        return;
      }
      error_(data.error || ("El servidor respondió con estado " + req.status + "."));
    };
    req.onerror = function () {
      error_("No se pudo enviar el formulario. Revisa tu conexión e inténtalo otra vez.");
    };

    req.send(datos);
  }

  function vigilar(id, redirect) {
    var base = document.body.getAttribute("data-trabajo-base") || "";
    var url = base.replace("ID", encodeURIComponent(id));

    function fallaRed() {
      fallosRed += 1;
      if (fallosRed >= 4) {
        error_("Se perdió la conexión con el servidor. Tu trabajo puede seguir "
               + "ejecutándose: pulsa reintentar para verlo.");
        return;
      }
      fase("Reconectando... (" + fallosRed + ")");
      window.setTimeout(consulta, 1500);
    }

    function consulta() {
      var req = new XMLHttpRequest();
      req.open("GET", url, true);
      req.onload = function () {
        if (req.status === 404) {
          error_("Este trabajo ya no existe. Vuelve a enviar el formulario.");
          return;
        }
        if (req.status !== 200) { fallaRed(); return; }
        var t;
        try { t = JSON.parse(req.responseText); } catch (e) { fallaRed(); return; }
        fallosRed = 0;
        if (t && typeof t.pct === "number") {
          objetivo = Math.max(objetivo, Math.round(30 + t.pct * 0.7));
          pintar();
        }
        if (t && t.fase) { fase(t.fase); }
        if (!t) { fallaRed(); return; }

        if (t.estado === "listo") {
          objetivo = 100;
          valor = 100;
          pintar();
          fase("¡Listo!");
          window.setTimeout(function () {
            window.location.href = redirect || window.location.href;
          }, 450);
          return;
        }
        if (t.estado === "error") {
          error_(t.error || "El trabajo no se pudo completar.");
          return;
        }
        window.setTimeout(consulta, 700);
      };
      req.onerror = fallaRed;
      req.send();
    }

    window.setTimeout(consulta, 700);
  }

  /* ---------------- arranque ---------------- */

  function iniciar() {
    overlay = el("loading-overlay");
    if (!overlay) { return; }
    bar = el("progress-bar");
    pct = el("progress-pct");
    titleEl = el("loading-title");
    subEl = el("loading-subtitle");
    faseEl = el("progress-fase");
    cajaError = el("loading-error");
    btnReintentar = el("loading-retry");

    if (btnReintentar) {
      btnReintentar.addEventListener("click", function () {
        if (fallo === "vigilar" && ultimoTrabajo) {
          mostrar(titleEl.textContent, "Reconectando con el trabajo...", true);
          fallosRed = 0;
          vigilar(ultimoTrabajo, ultimoRedirect);
          return;
        }
        if (ultimoForm) { enviar(ultimoForm); return; }
        ocultar();
      });
    }

    var forms = document.querySelectorAll("form");
    for (var i = 0; i < forms.length; i++) {
      var f = forms[i];
      var asincrono = f.hasAttribute("data-async");
      var pesado = asincrono || f.hasAttribute("data-cargando") ||
                   f.querySelector('input[type="file"]');
      if (!pesado) { continue; }
      f.addEventListener("submit", function (e) {
        if (this.hasAttribute("data-async")) {
          e.preventDefault();
          enviar(this);
          return;
        }
        mostrar(this.getAttribute("data-titulo"), this.getAttribute("data-sub"), false);
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
