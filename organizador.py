# -*- coding: utf-8 -*-
"""
ORGANIZADOR DE DOCUMENTOS DE ESTUDIANTES
Sistema Integral de Gestion Documental

3 herramientas:
  1. Convertir texto  -> MAYUSCULA / minuscula / Tipo Titulo
  2. Crear estructura -> carpetas por estudiante con su nomenclatura
  3. Normalizar       -> renombrar carpetas y archivos existentes
"""
import os
import re
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import inteligencia as intel
    _INTEL_OK = True
except Exception as _e:
    intel = None
    _INTEL_OK = False
    _INTEL_ERR = str(_e)


# ----------------------------------------------------------------------
# CONFIGURACION
# ----------------------------------------------------------------------
# (numero, nombre del documento, solo_menores)
DOCS = [
    ("001", "ACTA DE COMPROMISO", False),
    ("002", "DOCUMENTO DE IDENTIDAD", False),
    ("003", "CERTIFICADO ACADEMICO", False),
    ("004", "CERTIFICADO EPS", False),
    ("005", "TRATAMIENTO DE DATOS", True),
    ("006", "REGISTRO CIVIL", True),
    ("007", "DOCUMENTO TUTOR LEGAL", True),
]

# Tipos de documento (se guardan en MAYUSCULA siempre)
TIPOS = ["CC", "TI", "CE", "PP", "RC", "NIT"]

# Siglas que se mantienen en mayuscula al usar "Tipo Titulo"
SIGLAS = {"CC", "TI", "CE", "PP", "RC", "NIT", "EPS", "SISBEN", "PDF", "ID"}

SEP = "_"


# ----------------------------------------------------------------------
# LOGICA DE FORMATO
# ----------------------------------------------------------------------
def formatear(texto, modo):
    """modo: 'upper' | 'lower' | 'title'. Respeta siglas en 'title'."""
    texto = texto.strip()
    if modo == "upper":
        return texto.upper()
    if modo == "lower":
        return texto.lower()
    # tipo titulo
    partes = re.split(r"([ _])", texto)
    salida = []
    for p in partes:
        if p in (" ", "_") or p == "":
            salida.append(p)
        elif p.upper() in SIGLAS:
            salida.append(p.upper())
        else:
            salida.append(p.capitalize())
    return "".join(salida)


def limpiar_espacios(texto):
    texto = texto.strip()
    texto = re.sub(r"\s+", " ", texto)
    return texto


def nombre_carpeta(nombre, tipo, numero, modo):
    """SANTIAGO_BARRERA_CC_1031649321"""
    nombre = limpiar_espacios(nombre)
    nombre = nombre.replace(" ", SEP)
    nombre = nombre.replace("-", SEP)
    nombre = re.sub(r"_+", SEP, nombre)
    tipo = tipo.upper().strip()
    numero = re.sub(r"[^0-9A-Za-z]", "", numero)
    base = SEP.join([nombre, tipo, numero])
    return formatear(base, modo)


def nombre_documento(numero, nombre_doc, modo, ext=""):
    nombre_doc = nombre_doc.replace(" ", SEP)
    base = SEP.join([numero, nombre_doc])
    return formatear(base, modo) + ext


# ----------------------------------------------------------------------
# APP
# ----------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Organizador de Documentos de Estudiantes")
        self.geometry("960x720")
        self.minsize(860, 640)
        self.configure(bg="#F5F7FA")

        estilo = ttk.Style(self)
        try:
            estilo.theme_use("clam")
        except Exception:
            pass
        estilo.configure("TNotebook.Tab", padding=(18, 10), font=("Segoe UI", 10, "bold"))
        estilo.configure("TButton", padding=(12, 8), font=("Segoe UI", 10))
        estilo.configure("Accion.TButton", font=("Segoe UI", 11, "bold"))
        estilo.configure("TLabel", background="#F5F7FA", font=("Segoe UI", 10))

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_texto = ttk.Frame(nb)
        self.tab_crear = ttk.Frame(nb)
        self.tab_norm = ttk.Frame(nb)
        self.tab_clasif = ttk.Frame(nb)
        self.tab_separar = ttk.Frame(nb)
        nb.add(self.tab_texto, text="  1. Convertir texto  ")
        nb.add(self.tab_crear, text="  2. Crear estructura  ")
        nb.add(self.tab_norm, text="  3. Normalizar carpetas  ")
        nb.add(self.tab_clasif, text="  4. Clasificar documentos  ")
        nb.add(self.tab_separar, text="  5. Separar PDF grande  ")

        self._build_texto()
        self._build_crear()
        self._build_norm()
        self._build_clasif()
        self._build_separar()

    # ------------------------------------------------------------------
    # util
    # ------------------------------------------------------------------
    def _selector_modo(self, parent, variable):
        fr = ttk.Frame(parent)
        for txt, val in [("MAYÚSCULAS", "upper"), ("minúsculas", "lower"), ("Tipo Título", "title")]:
            ttk.Radiobutton(fr, text=txt, value=val, variable=variable).pack(side="left", padx=6)
        return fr

    # ==================================================================
    # PESTAÑA 1 - CONVERTIR TEXTO
    # ==================================================================
    def _build_texto(self):
        p = self.tab_texto
        ttk.Label(p, text="Convierte un nombre al formato que necesites", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
        ttk.Label(p, text="Escribe el nombre y elige el formato. Abajo ves el resultado en los 3 estilos.").pack(anchor="w", padx=16)

        self.var_modo_texto = tk.StringVar(value="upper")
        ttk.Label(p, text="Formato:").pack(anchor="w", padx=16, pady=(14, 2))
        self._selector_modo(p, self.var_modo_texto).pack(anchor="w", padx=16)

        ttk.Label(p, text="Texto:").pack(anchor="w", padx=16, pady=(12, 2))
        self.ent_texto = ttk.Entry(p, font=("Segoe UI", 12))
        self.ent_texto.pack(fill="x", padx=16)
        self.ent_texto.insert(0, "Santiago Barrera CC 1031649321")
        self.ent_texto.bind("<KeyRelease>", lambda e: self._preview_texto())

        ttk.Button(p, text="Convertir", style="Accion.TButton", command=self._preview_texto).pack(anchor="w", padx=16, pady=10)

        self.out_texto = scrolledtext.ScrolledText(p, height=8, font=("Consolas", 12), bg="#FFFFFF", relief="flat")
        self.out_texto.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        self._preview_texto()

    def _preview_texto(self):
        raw = self.ent_texto.get()
        modo = self.var_modo_texto.get()
        lineas = []
        lineas.append("MAYÚSCULAS :  " + formatear(raw, "upper"))
        lineas.append("minúsculas :  " + formatear(raw, "lower"))
        lineas.append("Tipo Título:  " + formatear(raw, "title"))
        lineas.append("")
        lineas.append("-- como carpeta principal (con guiones bajos) --")
        tokens = limpiar_espacios(raw).replace(" ", "_")
        lineas.append("MAYÚSCULAS :  " + formatear(tokens, "upper"))
        lineas.append("minúsculas :  " + formatear(tokens, "lower"))
        lineas.append("Tipo Título:  " + formatear(tokens, "title"))
        self.out_texto.delete("1.0", "end")
        self.out_texto.insert("end", "\n".join(lineas))

    # ==================================================================
    # PESTAÑA 2 - CREAR ESTRUCTURA
    # ==================================================================
    def _build_crear(self):
        p = self.tab_crear
        ttk.Label(p, text="Crea la carpeta de cada estudiante con sus 7 documentos", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
        ttk.Label(p, text="Un estudiante por línea con este formato:   Nombre Apellido, Numero, S/N      (S = menor de edad)").pack(anchor="w", padx=16)
        ttk.Label(p, text='Ejemplo:   Santiago Barrera, 1031649321, N', font=("Consolas", 10), foreground="#2F855A").pack(anchor="w", padx=16)

        cont = ttk.Frame(p)
        cont.pack(fill="x", padx=16, pady=(12, 0))
        ttk.Label(cont, text="Tipo documento:").pack(side="left")
        self.var_tipo = tk.StringVar(value="CC")
        ttk.Combobox(cont, textvariable=self.var_tipo, values=TIPOS, width=6, state="readonly").pack(side="left", padx=(6, 20))
        ttk.Label(cont, text="Formato:").pack(side="left")
        self.var_modo_crear = tk.StringVar(value="upper")
        self._selector_modo(cont, self.var_modo_crear).pack(side="left", padx=6)

        cont2 = ttk.Frame(p)
        cont2.pack(fill="x", padx=16, pady=(10, 0))
        ttk.Label(cont2, text="¿Crear como?").pack(side="left")
        self.var_como = tk.StringVar(value="carpetas")
        ttk.Radiobutton(cont2, text="Carpetas", value="carpetas", variable=self.var_como).pack(side="left", padx=6)
        ttk.Radiobutton(cont2, text="Archivos PDF vacíos", value="pdf", variable=self.var_como).pack(side="left", padx=6)

        cont3 = ttk.Frame(p)
        cont3.pack(fill="x", padx=16, pady=(10, 0))
        ttk.Label(cont3, text="Carpeta destino:").pack(side="left")
        self.var_destino = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Documents", "ESTUDIANTES"))
        ttk.Entry(cont3, textvariable=self.var_destino).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(cont3, text="Elegir...", command=self._elegir_destino).pack(side="left")

        ttk.Label(p, text="Estudiantes:").pack(anchor="w", padx=16, pady=(12, 2))
        self.txt_est = scrolledtext.ScrolledText(p, height=9, font=("Consolas", 11), bg="#FFFFFF", relief="flat")
        self.txt_est.pack(fill="both", expand=True, padx=16)
        self.txt_est.insert("end", "Santiago Barrera, 1031649321, N\nAna Gomez, 654321, S\n")

        bf = ttk.Frame(p)
        bf.pack(fill="x", padx=16, pady=12)
        ttk.Button(bf, text="Ver vista previa", command=self._preview_crear).pack(side="left")
        ttk.Button(bf, text="CREAR CARPETAS", style="Accion.TButton", command=self._crear).pack(side="right")

    def _elegir_destino(self):
        d = filedialog.askdirectory(title="Elige la carpeta donde crear todo")
        if d:
            self.var_destino.set(d)

    def _parse_estudiantes(self):
        out = []
        for linea in self.txt_est.get("1.0", "end").splitlines():
            linea = linea.strip()
            if not linea:
                continue
            partes = [x.strip() for x in re.split(r"[,\t;|]", linea) if x.strip()]
            if len(partes) < 2:
                continue
            nombre = partes[0]
            numero = partes[1]
            menor = len(partes) > 2 and partes[2].upper().startswith("S")
            out.append((nombre, numero, menor))
        return out

    def _estructura(self):
        modo = self.var_modo_crear.get()
        tipo = self.var_tipo.get()
        ests = self._parse_estudiantes()
        resultado = []
        for nombre, numero, menor in ests:
            carpeta = nombre_carpeta(nombre, tipo, numero, modo)
            docs = []
            for num, doc, solo_menores in DOCS:
                if solo_menores and not menor:
                    continue
                if self.var_como.get() == "pdf":
                    docs.append(nombre_documento(num, doc, modo, ".pdf"))
                else:
                    docs.append(nombre_documento(num, doc, modo, ""))
            resultado.append((carpeta, docs))
        return resultado

    def _preview_crear(self):
        res = self._estructura()
        if not res:
            messagebox.showwarning("Sin datos", "No se encontraron estudiantes válidos.")
            return
        win = tk.Toplevel(self)
        win.title("Vista previa")
        win.geometry("620x600")
        txt = scrolledtext.ScrolledText(win, font=("Consolas", 11), bg="#FFFFFF", relief="flat")
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        for carpeta, docs in res:
            txt.insert("end", carpeta + "/\n")
            for d in docs:
                txt.insert("end", "    " + d + "\n")
            txt.insert("end", "\n")

    def _crear(self):
        res = self._estructura()
        if not res:
            messagebox.showwarning("Sin datos", "No se encontraron estudiantes válidos.")
            return
        destino = self.var_destino.get()
        if not destino:
            messagebox.showwarning("Falta destino", "Elige una carpeta destino.")
            return
        try:
            os.makedirs(destino, exist_ok=True)
            creados = 0
            for carpeta, docs in res:
                ruta = os.path.join(destino, carpeta)
                os.makedirs(ruta, exist_ok=True)
                for d in docs:
                    if d.lower().endswith(".pdf"):
                        r = os.path.join(ruta, d)
                        if not os.path.exists(r):
                            with open(r, "wb") as f:
                                f.write(b"%PDF-1.4\n%%EOF\n")
                    else:
                        os.makedirs(os.path.join(ruta, d), exist_ok=True)
                creados += 1
            messagebox.showinfo("Listo", f"Se crearon {creados} carpetas de estudiantes en:\n{destino}")
            os.startfile(destino)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ==================================================================
    # PESTAÑA 3 - NORMALIZAR CARPETAS EXISTENTES
    # ==================================================================
    def _build_norm(self):
        p = self.tab_norm
        ttk.Label(p, text="Cambia el formato de carpetas y archivos que YA existen", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
        ttk.Label(p, text="Elige una carpeta raíz y el formato. Primero mira la vista previa, luego aplica.").pack(anchor="w", padx=16)

        cont = ttk.Frame(p)
        cont.pack(fill="x", padx=16, pady=(12, 0))
        ttk.Label(cont, text="Carpeta raíz:").pack(side="left")
        self.var_raiz = tk.StringVar()
        ttk.Entry(cont, textvariable=self.var_raiz).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(cont, text="Elegir...", command=self._elegir_raiz).pack(side="left")

        cont2 = ttk.Frame(p)
        cont2.pack(fill="x", padx=16, pady=(12, 0))
        ttk.Label(cont2, text="Formato:").pack(side="left")
        self.var_modo_norm = tk.StringVar(value="upper")
        self._selector_modo(cont2, self.var_modo_norm).pack(side="left", padx=6)
        self.var_recursivo = tk.BooleanVar(value=True)
        ttk.Checkbutton(cont2, text="Incluir subcarpetas", variable=self.var_recursivo).pack(side="left", padx=20)
        self.var_tambien_archivos = tk.BooleanVar(value=True)
        ttk.Checkbutton(cont2, text="También archivos", variable=self.var_tambien_archivos).pack(side="left")

        bf = ttk.Frame(p)
        bf.pack(fill="x", padx=16, pady=12)
        ttk.Button(bf, text="Vista previa", command=self._preview_norm).pack(side="left")
        ttk.Button(bf, text="APLICAR CAMBIOS", style="Accion.TButton", command=self._aplicar_norm).pack(side="right")

        self.txt_norm = scrolledtext.ScrolledText(p, font=("Consolas", 10), bg="#FFFFFF", relief="flat")
        self.txt_norm.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _elegir_raiz(self):
        d = filedialog.askdirectory(title="Elige la carpeta raíz")
        if d:
            self.var_raiz.set(d)

    def _plan_norm(self):
        raiz = self.var_raiz.get()
        modo = self.var_modo_norm.get()
        if not raiz or not os.path.isdir(raiz):
            return []
        plan = []
        if self.var_recursivo.get():
            caminar = os.walk(raiz, topdown=False)
        else:
            caminar = [(raiz, [d for d in os.listdir(raiz) if os.path.isdir(os.path.join(raiz, d))],
                        [f for f in os.listdir(raiz) if os.path.isfile(os.path.join(raiz, f))])]
        for actual, dirs, files in caminar:
            if self.var_tambien_archivos.get():
                for f in files:
                    nuevo = self._renombrar_preservando_ext(f, modo)
                    if nuevo != f:
                        plan.append((os.path.join(actual, f), os.path.join(actual, nuevo)))
            for d in dirs:
                nuevo = formatear(d, modo)
                if nuevo != d:
                    plan.append((os.path.join(actual, d), os.path.join(actual, nuevo)))
        return plan

    def _renombrar_preservando_ext(self, archivo, modo):
        nombre, ext = os.path.splitext(archivo)
        return formatear(nombre, modo) + ext

    def _preview_norm(self):
        plan = self._plan_norm()
        self.txt_norm.delete("1.0", "end")
        if not plan:
            self.txt_norm.insert("end", "No hay cambios que aplicar (ya está en ese formato) o la carpeta no existe.")
            return
        self.txt_norm.insert("end", f"{len(plan)} cambios:\n\n")
        for viejo, nuevo in plan:
            self.txt_norm.insert("end", os.path.basename(viejo) + "\n   -> " + os.path.basename(nuevo) + "\n")

    def _aplicar_norm(self):
        plan = self._plan_norm()
        if not plan:
            messagebox.showinfo("Sin cambios", "No hay cambios que aplicar.")
            return
        if not messagebox.askyesno("Confirmar", f"¿Aplicar {len(plan)} cambios de nombre?"):
            return
        errores = 0
        for viejo, nuevo in plan:
            try:
                if os.path.exists(viejo) and not os.path.exists(nuevo):
                    os.rename(viejo, nuevo)
                else:
                    errores += 1
            except Exception:
                errores += 1
        messagebox.showinfo("Listo", f"Se aplicaron {len(plan) - errores} cambios. Con errores: {errores}.")

    # ==================================================================
    # PESTAÑA 4 - CLASIFICAR DOCUMENTOS (IA / OCR local)
    # ==================================================================
    def _build_clasif(self):
        p = self.tab_clasif
        ttk.Label(p, text="Lee cada documento e identifica qué tipo es", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
        if _INTEL_OK and intel._ocr_disponible():
            estado = "Lectura inteligente LISTA  ·  OCR en español instalado  ·  100 % local"
            color = "#2F855A"
        elif _INTEL_OK:
            estado = "Falta el idioma español de Tesseract (spa.traineddata). Solo podrá leer PDF con texto."
            color = "#B7791F"
        else:
            estado = "No se pudo cargar inteligencia.py: " + _INTEL_ERR
            color = "#C53030"
        ttk.Label(p, text=estado, foreground=color).pack(anchor="w", padx=16)
        ttk.Label(p, text="Selecciona una carpeta con PDF o imágenes, pulsa Analizar y revisa el tipo detectado.").pack(anchor="w", padx=16, pady=(2, 8))

        cont = ttk.Frame(p)
        cont.pack(fill="x", padx=16)
        ttk.Label(cont, text="Carpeta:").pack(side="left")
        self.var_clasif_dir = tk.StringVar()
        ttk.Entry(cont, textvariable=self.var_clasif_dir).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(cont, text="Elegir...", command=self._elegir_clasif).pack(side="left")

        cont2 = ttk.Frame(p)
        cont2.pack(fill="x", padx=16, pady=(10, 0))
        ttk.Button(cont2, text="Añadir archivos...", command=self._add_archivos_clasif).pack(side="left")
        ttk.Button(cont2, text="ANALIZAR", style="Accion.TButton", command=self._analizar_clasif).pack(side="left", padx=8)
        ttk.Button(cont2, text="Limpiar lista", command=self._limpiar_clasif).pack(side="left")
        self.lbl_progreso = ttk.Label(cont2, text="")
        self.lbl_progreso.pack(side="left", padx=12)

        cols = ("archivo", "tipo", "conf")
        self.tree_clasif = ttk.Treeview(p, columns=cols, show="headings", height=11)
        self.tree_clasif.heading("archivo", text="Archivo")
        self.tree_clasif.heading("tipo", text="Tipo detectado")
        self.tree_clasif.heading("conf", text="Confianza")
        self.tree_clasif.column("archivo", width=430)
        self.tree_clasif.column("tipo", width=280)
        self.tree_clasif.column("conf", width=110, anchor="center")
        self.tree_clasif.pack(fill="both", expand=True, padx=16, pady=(12, 6))
        self.tree_clasif.bind("<<TreeviewSelect>>", self._sel_clasif)

        cont3 = ttk.Frame(p)
        cont3.pack(fill="x", padx=16)
        ttk.Label(cont3, text="Corregir tipo de lo seleccionado:").pack(side="left")
        self.var_tipo_manual = tk.StringVar()
        opciones = [f"{n}_{nom}" for n, nom, _ in DOCS] + ["(dejar como está)"]
        self.cmb_tipo_manual = ttk.Combobox(cont3, textvariable=self.var_tipo_manual, values=opciones, width=34, state="readonly")
        self.cmb_tipo_manual.pack(side="left", padx=8)
        self.cmb_tipo_manual.set("(dejar como está)")
        ttk.Button(cont3, text="Aplicar a seleccionados", command=self._aplicar_manual_clasif).pack(side="left")

        cont4 = ttk.Frame(p)
        cont4.pack(fill="x", padx=16, pady=(10, 16))
        ttk.Label(cont4, text="Formato del nombre:").pack(side="left")
        self.var_modo_clasif = tk.StringVar(value="upper")
        self._selector_modo(cont4, self.var_modo_clasif).pack(side="left", padx=6)
        ttk.Button(cont4, text="RENOMBRAR ARCHIVOS", style="Accion.TButton", command=self._renombrar_clasif).pack(side="right")

        self.clasif_items = []

    def _elegir_clasif(self):
        d = filedialog.askdirectory(title="Elige la carpeta con los documentos")
        if d:
            self.var_clasif_dir.set(d)

    def _add_archivos_clasif(self):
        archivos = filedialog.askopenfilenames(
            title="Elige documentos",
            filetypes=[("PDF e imágenes", "*.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp"),
                       ("Todos", "*.*")])
        for a in archivos:
            self.clasif_items.append({"ruta": a, "tipo": "", "conf": "", "nombre": os.path.basename(a)})
        self._refrescar_tree_clasif()

    def _refrescar_tree_clasif(self):
        self.tree_clasif.delete(*self.tree_clasif.get_children())
        for it in self.clasif_items:
            self.tree_clasif.insert("", "end", values=(os.path.basename(it["ruta"]), it["tipo"], it["conf"]))

    def _limpiar_clasif(self):
        self.clasif_items = []
        self._refrescar_tree_clasif()
        self.lbl_progreso.config(text="")

    def _analizar_clasif(self):
        if not _INTEL_OK:
            messagebox.showerror("Error", "No se pudo cargar el motor de clasificación.")
            return
        carpeta = self.var_clasif_dir.get()
        if carpeta and os.path.isdir(carpeta):
            for f in sorted(os.listdir(carpeta)):
                ext = os.path.splitext(f)[1].lower()
                if ext in intel.EXT_PDF or ext in intel.EXT_IMAGEN:
                    ruta = os.path.join(carpeta, f)
                    if not any(it["ruta"] == ruta for it in self.clasif_items):
                        self.clasif_items.append({"ruta": ruta, "tipo": "", "conf": "", "nombre": f})
        if not self.clasif_items:
            messagebox.showwarning("Sin archivos", "Elige una carpeta con documentos o añade archivos.")
            return
        self._refrescar_tree_clasif()
        hilo = threading.Thread(target=self._trabajo_analizar, daemon=True)
        hilo.start()

    def _trabajo_analizar(self):
        total = len(self.clasif_items)
        for i, it in enumerate(self.clasif_items):
            self.after(0, lambda i=i, total=total: self.lbl_progreso.config(
                text=f"Analizando {i + 1}/{total}..."))
            try:
                texto, res = intel.clasificar_archivo(it["ruta"])
                if res:
                    num, nom, conf, _ = res
                    it["tipo"] = f"{num}_{nom}"
                    it["conf"] = conf
                else:
                    it["tipo"] = "(no identificado)"
                    it["conf"] = "-"
            except Exception:
                it["tipo"] = "(error al leer)"
                it["conf"] = "-"
            self.after(0, self._refrescar_tree_clasif)
        self.after(0, lambda: self.lbl_progreso.config(text=f"Listo: {total} documentos"))

    def _sel_clasif(self, _e=None):
        sel = self.tree_clasif.selection()
        if sel:
            vals = self.tree_clasif.item(sel[0], "values")
            if vals and vals[1] and vals[1] not in ("(no identificado)", "(error al leer)"):
                self.cmb_tipo_manual.set(vals[1])

    def _aplicar_manual_clasif(self):
        valor = self.var_tipo_manual.get()
        if valor == "(dejar como está)":
            return
        sel = self.tree_clasif.selection()
        idxs = [self.tree_clasif.index(s) for s in sel]
        for i in idxs:
            self.clasif_items[i]["tipo"] = valor
            self.clasif_items[i]["conf"] = "manual"
        self._refrescar_tree_clasif()

    def _renombrar_clasif(self):
        modo = self.var_modo_clasif.get()
        cont = 0
        errores = 0
        for it in self.clasif_items:
            tipo = it["tipo"]
            if not tipo or "_" not in tipo:
                errores += 1
                continue
            num, _, nom = tipo.partition("_")
            ext = os.path.splitext(it["ruta"])[1]
            nuevo_nombre = formatear(f"{num}_{nom}", modo) + ext
            carpeta = os.path.dirname(it["ruta"])
            destino = os.path.join(carpeta, nuevo_nombre)
            try:
                if os.path.abspath(destino) != os.path.abspath(it["ruta"]):
                    os.rename(it["ruta"], destino)
                    it["ruta"] = destino
                cont += 1
            except Exception:
                errores += 1
        self._refrescar_tree_clasif()
        messagebox.showinfo("Renombrado", f"Renombrados: {cont}. Omitidos con error: {errores}.")

    # ==================================================================
    # PESTAÑA 5 - SEPARAR UN PDF GRANDE EN DOCUMENTOS
    # ==================================================================
    def _build_separar(self):
        p = self.tab_separar
        ttk.Label(p, text="Separa un PDF único (con todo) en documentos individuales", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
        ttk.Label(p, text="Analiza página por página, detecta el tipo de cada una y corta donde cambia el documento.").pack(anchor="w", padx=16, pady=(0, 10))

        c1 = ttk.Frame(p)
        c1.pack(fill="x", padx=16)
        ttk.Label(c1, text="PDF grande:").pack(side="left")
        self.var_pdf_grande = tk.StringVar()
        ttk.Entry(c1, textvariable=self.var_pdf_grande).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(c1, text="Elegir PDF...", command=self._elegir_pdf_grande).pack(side="left")
        ttk.Button(c1, text="ANALIZAR", style="Accion.TButton", command=self._analizar_grande).pack(side="left", padx=8)

        self.lbl_prog_grande = ttk.Label(p, text="")
        self.lbl_prog_grande.pack(anchor="w", padx=16, pady=(8, 0))

        cols = ("pag", "tipo", "conf", "inicio")
        self.tree_grande = ttk.Treeview(p, columns=cols, show="headings", height=10)
        self.tree_grande.heading("pag", text="Pág.")
        self.tree_grande.heading("tipo", text="Tipo detectado")
        self.tree_grande.heading("conf", text="Conf.")
        self.tree_grande.heading("inicio", text="Primera línea")
        self.tree_grande.column("pag", width=55, anchor="center")
        self.tree_grande.column("tipo", width=270)
        self.tree_grande.column("conf", width=70, anchor="center")
        self.tree_grande.column("inicio", width=380)
        self.tree_grande.pack(fill="both", expand=True, padx=16, pady=(8, 6))
        self.tree_grande.tag_configure("cambio", background="#E8F1FF")

        c2 = ttk.Frame(p)
        c2.pack(fill="x", padx=16, pady=(4, 16))
        ttk.Label(c2, text="Destino:").pack(side="left")
        self.var_dest_grande = tk.StringVar()
        ttk.Entry(c2, textvariable=self.var_dest_grande).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(c2, text="Carpeta...", command=self._elegir_dest_grande).pack(side="left")
        ttk.Label(c2, text="Formato:").pack(side="left", padx=(10, 0))
        self.var_modo_grande = tk.StringVar(value="upper")
        self._selector_modo(c2, self.var_modo_grande).pack(side="left", padx=6)
        ttk.Button(c2, text="SEPARAR EN ARCHIVOS", style="Accion.TButton", command=self._separar_grande).pack(side="left", padx=8)

        self.grande_resultado = []

    def _elegir_pdf_grande(self):
        f = filedialog.askopenfilename(title="Elige el PDF grande",
                                       filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")])
        if f:
            self.var_pdf_grande.set(f)
            if not self.var_dest_grande.get():
                self.var_dest_grande.set(os.path.join(os.path.dirname(f), "documentos_separados"))

    def _elegir_dest_grande(self):
        d = filedialog.askdirectory(title="Carpeta de destino")
        if d:
            self.var_dest_grande.set(d)

    def _analizar_grande(self):
        if not _INTEL_OK:
            messagebox.showerror("Error", "No se pudo cargar el motor de análisis.")
            return
        ruta = self.var_pdf_grande.get()
        if not ruta or not os.path.isfile(ruta):
            messagebox.showwarning("Falta el PDF", "Elige un PDF válido.")
            return
        self.tree_grande.delete(*self.tree_grande.get_children())
        self.grande_resultado = []
        self.lbl_prog_grande.config(text="Analizando...")
        threading.Thread(target=self._trabajo_grande, args=(ruta,), daemon=True).start()

    def _trabajo_grande(self, ruta):
        paginas = intel.analizar_pdf_paginas(
            ruta,
            progreso=lambda i, t: self.after(0, lambda: self.lbl_prog_grande.config(text=f"Analizando página {i}/{t}...")),
            on_pagina=lambda info: self.after(0, self._add_pagina_grande, info),
        )
        self.after(0, self._fin_grande, paginas)

    def _add_pagina_grande(self, info):
        tipo = info["tipo"] or "(sin identificar)"
        self.tree_grande.insert("", "end", values=(info["pagina"], tipo, info["conf"] or "-", info["inicio"]))

    def _fin_grande(self, paginas):
        self.grande_resultado = paginas
        grupos = intel.agrupar_paginas(paginas)
        self.grande_grupos = grupos
        # Marca en azul la primera página de cada documento (donde corta)
        hijos = self.tree_grande.get_children()
        for g in grupos:
            idx = g["paginas"][0] - 1
            if 0 <= idx < len(hijos):
                self.tree_grande.item(hijos[idx], tags=("cambio",))
        self.lbl_prog_grande.config(
            text=f"Listo: {len(paginas)} páginas, {len(grupos)} documentos detectados (filas azules = inicio de documento)")

    def _separar_grande(self):
        if not getattr(self, "grande_grupos", None):
            messagebox.showwarning("Primero analiza", "Pulsa ANALIZAR antes de separar.")
            return
        destino = self.var_dest_grande.get()
        if not destino:
            messagebox.showwarning("Falta destino", "Elige la carpeta de destino.")
            return
        grupos = self.grande_grupos
        sin_ident = [g for g in grupos if not g["num"]]
        if sin_ident:
            ok = messagebox.askyesno(
                "Atención",
                f"{len(sin_ident)} bloque(s) no se identificaron y se guardarán como sin_identificar.\n¿Continuar?")
            if not ok:
                return
        try:
            creados = intel.separar_pdf(self.var_pdf_grande.get(), destino, grupos, modo=self.var_modo_grande.get())
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo separar:\n{e}")
            return
        messagebox.showinfo("Separado", f"Se crearon {len(creados)} archivos en:\n{destino}")


if __name__ == "__main__":
    App().mainloop()
