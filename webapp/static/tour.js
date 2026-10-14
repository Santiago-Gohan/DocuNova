/* =====================================================================
   DocuNova - Tour guiado (estilo product tour)
   Personajes tipo anime que explican cada parte de la app.
   Las imagenes son opcionales: si no existe el archivo, se usa un emoji.
   Coloca tus imagenes en:  webapp/static/tour/
   ===================================================================== */
(function () {
  "use strict";

  /* Pregunta inicial (solo se muestra con la sesion iniciada) */
  var INTRO = {
    id: "0_goku", emoji: "\uD83E\uDD4B", color: "#f97316",
    quien: "Goku", titulo: "\u00a1Hola! Soy Goku",
    texto: "\u00bfYa dominas las t\u00e9cnicas de este sistema o necesitas que te entrene desde cero con esta gu\u00eda interactiva?"
  };

  /* Pasos de la guia (despues de aceptar el entrenamiento) */
  var PASOS = [
    {
      id: "1_goku", emoji: "\uD83E\uDD4B", color: "#f97316",
      quien: "Goku", titulo: "\u00a1Bienvenido a DocuNova!",
      texto: "Esta es tu central para organizar los documentos del colegio. Aqu\u00ed ver\u00e1s todas las herramientas disponibles."
    },
    {
      id: "2_vegeta", emoji: "\uD83D\uDCAA", color: "#2563eb",
      quien: "Vegeta", titulo: "Entra y completa tu perfil",
      texto: "\u00a1Hmph! \u00a1No hay tiempo que perder! Entra a \u2018Mi perfil\u2019 para poner tu nombre y correo. Un guerrero siempre mantiene sus datos en orden."
    },
    {
      id: "3_bulma", emoji: "\uD83D\uDD27", color: "#0d9488",
      quien: "Bulma", titulo: "Mis documentos",
      texto: "\u00a1Hola, soy Bulma! Aqu\u00ed tienes tu carpeta privada: sube tus PDF o im\u00e1genes y el sistema detecta el tipo de documento solo. \u00a1Solo t\u00fa puedes ver estos archivos!"
    },
    {
      id: "4_piccolo", emoji: "\uD83E\uDDD8", color: "#16a34a",
      quien: "Piccolo", titulo: "Convertir texto",
      texto: "\u00a1Conc\u00e9ntrate! Escribe un nombre por l\u00ednea y ver\u00e1s el resultado en MAY\u00daSCULAS, min\u00fasculas y Tipo T\u00edtulo. Reserva tus siglas como CC, TI o EPS."
    },
    {
      id: "5_gohan", emoji: "\uD83D\uDCDA", color: "#7c3aed",
      quien: "Gohan", titulo: "Crear estructura de carpetas",
      texto: "Soy Gohan. Escribe los estudiantes (Nombre Apellido, N\u00famero, S/N) y te generar\u00e9 un ZIP con una carpeta por estudiante y todos sus documentos ya nombrados."
    },
    {
      id: "6_trunks", emoji: "\u2694\uFE0F", color: "#6366f1",
      quien: "Trunks", titulo: "Clasificar documentos",
      texto: "\u00a1R\u00e1pido y preciso! Sube varios PDF o im\u00e1genes; reconozco el tipo de cada uno con OCR y los renombro autom\u00e1ticamente. Al final te doy un ZIP con todo ordenado."
    },
    {
      id: "7_krillin", emoji: "\u2600\uFE0F", color: "#ea580c",
      quien: "Krillin", titulo: "Separar un PDF grande",
      texto: "\u00a1Hey! Si tienes un solo PDF con muchos documentos juntos, sube el archivo, analizo las p\u00e1ginas (uniendo frente y reverso) y lo divido en documentos sueltos."
    },
    {
      id: "8_chichi", emoji: "\uD83D\uDEE1\uFE0F", color: "#dc2626",
      quien: "Chi-Chi", titulo: "Tus datos est\u00e1n protegidos",
      texto: "Estos documentos tienen datos personales, as\u00ed que el reconocimiento de texto se hace en el servidor y no se env\u00edan a servicios externos. \u00a1La privacidad es lo primero!"
    },
    {
      id: "9_goten", emoji: "\u2728", color: "#eab308",
      quien: "Goten", titulo: "\u00bfTarda la primera vez?",
      texto: "\u00a1No te asustes! La primera carga puede tardar un poquito porque el servicio \u2018despierta\u2019. Despu\u00e9s ya vuela tan r\u00e1pido como yo."
    },
    {
      id: "10_videl", emoji: "\uD83C\uDFAF", color: "#db2777",
      quien: "Videl", titulo: "Mant\u00e9n tu cuenta segura",
      texto: "Soy Videl. Cambia tu contrase\u00f1a cuando quieras desde \u2018Mi perfil\u2019. Y si eres admin, puedes crear usuarios y resetear claves desde el panel de Administraci\u00f3n."
    },
    {
      id: "11_shenron", emoji: "\uD83D\uDC09", color: "#059669",
      quien: "Shenron", titulo: "\u00a1Entrenamiento completo!",
      texto: "\u00a1Has reunido las siete esferas! Ya conoces DocuNova. \u00a1Ve y organ\u00edzalo todo con tu m\u00e1ximo poder! Puedes volver a ver este recorrido con el bot\u00f3n \u2018\u00bfC\u00f3mo funciona?\u2019."
    }
  ];

  var CLAVE = "docunova_tour_v2";
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
    btnSig.textContent = (i === PASOS.length - 1) ? "Finalizar" : "Siguiente";
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
    void raiz.offsetWidth;            /* reinicia la animacion de entrada */
    raiz.classList.add("abierto");
    pintar();
  }

  function cerrar() {
    raiz.classList.remove("abierto");
    try { localStorage.setItem(CLAVE, "1"); } catch (e) {}
    window.setTimeout(function () { raiz.hidden = true; }, 260);
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
    el("tour-saltar").addEventListener("click", cerrar);
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
