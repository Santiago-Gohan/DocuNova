/* =====================================================================
   DocuNova - "Product Tour" flotante (componente modular y reutilizable)

   Como funciona:
   - El PERSONAJE (.tour-img) se superpone a la pagina real (posicion fija,
     abajo a la izquierda). No oscurece la pantalla.
   - La BURBUJA (.tour-burbuja) es un tooltip translucido moderno con el
     texto del paso, el contador ("1 de 10") y los botones.
   - Cada paso se define en el arreglo PASOS (abajo). Solo edita ese arreglo
     para cambiar textos, personajes, imagenes o el numero de pasos (1..10).

   Imagenes: se buscan en  webapp/static/tour/  con el nombre  "<id>.png".
   Si no existe el PNG se intenta .jpg / .jpeg / .webp y, si nada aparece,
   se muestra el emoji del personaje (nunca se ve una imagen rota).

   API publica:
     window.abrirTour()   -> abre el tour (lo usa el boton flotante 🐉 Guía)
   ===================================================================== */
(function () {
  "use strict";

  /* -------------------------------------------------------------------
     1) CONFIGURACION
     ------------------------------------------------------------------- */

  /* Pregunta inicial que ve el usuario la primera vez (solo logueado). */
  var INTRO = {
    id: "1_goku",               /* imagen a mostrar en la intro */
    emoji: "\uD83E\uDD4B",      /* 🥋 respaldo si falta la imagen */
    color: "#f97316",           /* color de la etiqueta del personaje */
    quien: "Goku",
    titulo: "\u00a1Hola! Soy Goku",
    texto: "\u00bfYa dominas las t\u00e9cnicas de este sistema o necesitas " +
           "que te entrene desde cero con esta gu\u00eda interactiva?"
  };

  /* -------------------------------------------------------------------
     PASOS DEL TOUR  (edita SOLO este arreglo)
     Campos de cada paso:
       id     -> nombre del archivo de imagen SIN extension  (ej: "1_goku")
       emoji  -> respaldo si no hay imagen
       color  -> color de la etiqueta con el nombre del personaje
       quien  -> nombre que se muestra en la etiqueta
       titulo -> titulo del paso
       texto  -> contenido que explica el personaje
       btn    -> texto del boton principal (por defecto "Siguiente")
     Para agregar/quitar pasos: copia o borra un bloque { ... }.
     El contador "n de N" se calcula solo segun el largo del arreglo.
     ------------------------------------------------------------------- */
  var PASOS = [
    {
      id: "1_goku", emoji: "\uD83E\uDD4B", color: "#f97316",
      quien: "Goku", titulo: "Bienvenida",
      texto: "\u00a1Hola! Soy Goku. Entra a tu 'Perfil' para empezar tu entrenamiento.",
      btn: "Siguiente"
    },
    {
      id: "2_vegeta", emoji: "\uD83D\uDCAA", color: "#2563eb",
      quien: "Vegeta", titulo: "Estad\u00edsticas",
      texto: "No pierdas tiempo, insecto. Ve al 'Dashboard' y revisa tus estad\u00edsticas.",
      btn: "Entendido"
    },
    {
      id: "3_bulma", emoji: "\uD83D\uDD27", color: "#0d9488",
      quien: "Bulma", titulo: "Herramientas",
      texto: "\u00a1Genial! A\u00f1ad\u00ed nuevas funciones. Pru\u00e9balas en la pesta\u00f1a 'Herramientas'.",
      btn: "Ver m\u00e1s"
    },
    {
      id: "4_krillin", emoji: "\uD83D\uDC51", color: "#ca8a04",
      quien: "Krillin", titulo: "Clasifica tus documentos",
      texto: "Con OCR local reconocemos el texto de tus PDFs. Ordena todo desde 'Clasificar' y 'Separar'.",
      btn: "Siguiente"
    },
    {
      id: "5_gohan", emoji: "\uD83D\uDCD8", color: "#16a34a",
      quien: "Gohan", titulo: "Crea tu estructura",
      texto: "Usa 'Crear' y 'Convertir' para generar la carpeta numerada 001..007 con tus documentos.",
      btn: "Siguiente"
    },
    {
      id: "6_personaje", emoji: "\uD83D\uDC09", color: "#b45309",
      quien: "Shenron", titulo: "Cierre del tour",
      texto: "\u00a1Felicidades! Has completado el entrenamiento. Ahora ve y usa tu poder.",
      btn: "Terminar"
    }

    /* --- Ejemplos para llegar hasta 10 pasos (descomenta y ajusta) ---
    ,
    {
      id: "7_personaje", emoji: "\u2705", color: "#7c3aed",
      quien: "Piccolo", titulo: "Paso 7",
      texto: "Escribe aqui tu explicacion.",
      btn: "Siguiente"
    },
    {
      id: "8_personaje", emoji: "\u2705", color: "#7c3aed",
      quien: "Trunks", titulo: "Paso 8",
      texto: "Escribe aqui tu explicacion.",
      btn: "Siguiente"
    },
    {
      id: "9_personaje", emoji: "\u2705", color: "#7c3aed",
      quien: "Chi-Chi", titulo: "Paso 9",
      texto: "Escribe aqui tu explicacion.",
      btn: "Siguiente"
    },
    {
      id: "10_personaje", emoji: "\u2705", color: "#7c3aed",
      quien: "Maestro Roshi", titulo: "Paso 10",
      texto: "Escribe aqui tu explicacion.",
      btn: "Terminar"
    }
    ------------------------------------------------------------------- */
  ];

  var CLAVE_VISTO = "docunova_tour_v3";  /* bandera en localStorage */
  var EXTENSIONES = ["png", "jpg", "jpeg", "webp"]; /* orden de intentos */

  /* -------------------------------------------------------------------
     2) ESTADO Y REFERENCIAS AL DOM
     ------------------------------------------------------------------- */
  var raiz;                 /* #tour (contenedor flotante) */
  var img, emoji, quien, titulo, texto;   /* personaje + textos */
  var contador, btnSig, btnAtras, puntos, nav, introBox;
  var enIntro = true;       /* true = mostrando la pregunta inicial */
  var idx = 0;              /* indice actual dentro de PASOS */

  function el(id) { return document.getElementById(id); }

  /* -------------------------------------------------------------------
     3) PINTAR EL PERSONAJE Y LOS TEXTOS DE UN PASO
     ------------------------------------------------------------------- */
  function pintarBurbuja(p) {
    var base = raiz.getAttribute("data-imgbase") || "/static/tour/";

    /* Intenta <base><id>.png; si falla prueba .jpg/.jpeg/.webp y al final emoji */
    var i = 0;
    img.onerror = function () {
      i++;
      if (i >= EXTENSIONES.length) {           /* se agotaron: usar emoji */
        img.style.display = "none";
        emoji.style.display = "block";
      } else {
        img.src = base + p.id + "." + EXTENSIONES[i];
      }
    };
    img.style.display = "";
    emoji.style.display = "none";
    img.src = base + p.id + "." + EXTENSIONES[0];
    img.alt = p.quien;

    emoji.textContent = p.emoji;
    quien.textContent = p.quien;
    quien.style.background = p.color;
    titulo.textContent = p.titulo;
    texto.textContent = p.texto;
  }

  /* -------------------------------------------------------------------
     4) PINTAR TODA LA VISTA (intro o paso normal)
     ------------------------------------------------------------------- */
  function pintar() {
    if (enIntro) {                       /* --- vista de la pregunta --- */
      pintarBurbuja(INTRO);
      contador.textContent = "";
      puntos.style.display = "none";
      nav.style.display = "none";
      introBox.style.display = "flex";
      return;
    }

    /* --- vista de un paso normal --- */
    var p = PASOS[idx];
    pintarBurbuja(p);
    contador.textContent = (idx + 1) + " de " + PASOS.length;
    btnAtras.style.visibility = idx === 0 ? "hidden" : "visible";
    btnSig.textContent = p.btn || "Siguiente";

    /* puntos de progreso */
    var html = "";
    for (var k = 0; k < PASOS.length; k++) {
      html += '<i class="' + (k === idx ? "on" : "") + '"></i>';
    }
    puntos.innerHTML = html;
    puntos.style.display = "flex";
    nav.style.display = "flex";
    introBox.style.display = "none";
  }

  /* -------------------------------------------------------------------
     5) ACCIONES PRINCIPALES: abrir / avanzar / retroceder / cerrar
     ------------------------------------------------------------------- */
  function abrir() {                     /* muestra el tour desde el inicio */
    enIntro = true;
    idx = 0;
    raiz.hidden = false;
    void raiz.offsetWidth;               /* fuerza reflow para animar */
    raiz.classList.add("abierto");
    pintar();
  }

  function avanzar() {                   /* boton principal */
    if (enIntro) { enIntro = false; idx = 0; pintar(); return; }
    if (idx >= PASOS.length - 1) { cerrar(); return; }  /* ultimo paso */
    idx++;
    pintar();
  }

  function retroceder() {                /* boton "Atras" */
    if (enIntro || idx === 0) { return; }
    idx--;
    pintar();
  }

  function cerrar() {                    /* cierra y recuerda que ya se vio */
    raiz.classList.remove("abierto");
    try { localStorage.setItem(CLAVE_VISTO, "1"); } catch (e) {}
    window.setTimeout(function () { raiz.hidden = true; }, 300);
  }

  /* -------------------------------------------------------------------
     6) INICIALIZACION: toma referencias y enlaza eventos
     ------------------------------------------------------------------- */
  function iniciar() {
    raiz = el("tour");
    if (!raiz) { return; }               /* no hay tour en esta pagina */

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

    /* Botones de la burbuja */
    btnSig.addEventListener("click", avanzar);
    btnAtras.addEventListener("click", retroceder);
    el("tour-cerrar").addEventListener("click", cerrar);

    /* Botones de la pregunta inicial */
    el("tour-experto").addEventListener("click", cerrar);        /* ya sabe */
    el("tour-maestro").addEventListener("click", function () {   /* ensenar */
      enIntro = false; idx = 0; pintar();
    });

    /* Atajos de teclado: Esc = cerrar, flechas = navegar */
    document.addEventListener("keydown", function (ev) {
      if (raiz.hidden) { return; }
      if (ev.key === "Escape") { cerrar(); }
      if (enIntro) { return; }
      if (ev.key === "ArrowRight") { avanzar(); }
      if (ev.key === "ArrowLeft") { retroceder(); }
    });

    /* Expone la API publica para el boton flotante */
    window.abrirTour = abrir;

    /* Abre solo la primera vez (si el usuario no lo ha cerrado antes) */
    var visto = false;
    try { visto = localStorage.getItem(CLAVE_VISTO) === "1"; } catch (e) {}
    if (!visto) { window.setTimeout(abrir, 700); }
  }

  /* Arranca cuando el DOM esta listo */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
