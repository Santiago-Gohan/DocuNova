# -*- coding: utf-8 -*-
"""
Trabajos en segundo plano con progreso real.

Idea: el servidor NO hace el trabajo dentro de la peticion HTTP. La peticion
solo recibe los archivos, lanza un hilo y devuelve un id al instante. Mientras
tanto el navegador consulta  GET /trabajo/<id>  cada poco tiempo y pinta el
avance real.

Con esto:
  * ninguna peticion dura mas de un segundo  ->  el proxy de Render no la corta
    (el corte a los ~100s era el motivo de la barra congelada en 92%).
  * un solo OCR a la vez  ->  no se revienta la memoria (512 MB en plan free)
    y la cola no se traba por compartir CPU.
  * si el cliente pierde la conexion o el trabajo muere, el estado termina en
    "error" con un mensaje, en lugar de una barra infinita.

Nota: el registro de trabajos vive en memoria, asi que este modulo asume UN
solo proceso (el Dockerfile usa  gunicorn -w 1 --threads 8 ). Si algun dia se
escala a varios workers o instancias, el id del trabajo tendria que guardarse
en un almacen compartido (la base de datos o Redis).
"""
import threading
import time
import uuid

_LOCK = threading.Lock()
_TRABAJOS = {}

# Un solo proceso pesado a la vez. El segundo usuario ve su posicion en cola.
_SEMAFORO = threading.Semaphore(1)

VIDA = 60 * 60              # trabajos terminados se borran a la hora
ESPERA_COLA = 45 * 60       # tiempo maximo esperando el turno
MAX_GUARDADOS = 40


def _podar(borrar_activos=False):
    ahora = time.time()
    viejos = [k for k, t in _TRABAJOS.items()
              if t["estado"] in ("listo", "error") and ahora - t["creado"] > VIDA]
    for k in viejos:
        _TRABAJOS.pop(k, None)
    while len(_TRABAJOS) > MAX_GUARDADOS:
        # se descartan primero los terminados mas antiguos
        terminados = [k for k, t in _TRABAJOS.items()
                      if t["estado"] in ("listo", "error")]
        if not terminados:
            break
        mas_viejo = min(terminados, key=lambda k: _TRABAJOS[k]["creado"])
        _TRABAJOS.pop(mas_viejo, None)


def crear(uid, titulo, funcion, *args, **kwargs):
    """Lanza `funcion(progreso, *args, **kwargs)` en un hilo y devuelve su id.

    `progreso(pct, fase)` es lo que la funcion debe llamar para reportar
    avance (pct entre 0 y 99).
    """
    tid = uuid.uuid4().hex[:12]
    trabajo = {
        "id": tid, "uid": uid, "titulo": titulo,
        "estado": "cola", "pct": 0, "fase": "En cola",
        "error": None, "resultado": None, "creado": time.time(),
    }
    with _LOCK:
        _podar()
        _TRABAJOS[tid] = trabajo
    hilo = threading.Thread(target=_ejecutar, args=(trabajo, funcion, args, kwargs),
                            daemon=True)
    hilo.start()
    return tid


def _ejecutar(trabajo, funcion, args, kwargs):
    adquirio = _SEMAFORO.acquire(timeout=ESPERA_COLA)
    if not adquirio:
        with _LOCK:
            trabajo.update(estado="error", fase="No se pudo iniciar",
                           error="Hay varios procesos en cola. Inténtalo de nuevo "
                                 "en unos minutos.")
        return
    try:
        with _LOCK:
            trabajo.update(estado="procesando", fase="Preparando...")

        def progreso(pct, fase=None):
            with _LOCK:
                try:
                    trabajo["pct"] = max(0, min(99, int(pct)))
                except (TypeError, ValueError):
                    pass
                if fase:
                    trabajo["fase"] = str(fase)[:160]

        resultado = funcion(progreso, *args, **kwargs)
        with _LOCK:
            trabajo.update(estado="listo", pct=100, fase="¡Listo!",
                           resultado=resultado)
    except Exception as exc:  # noqa: BLE001 - cualquier fallo va al cliente
        with _LOCK:
            trabajo.update(estado="error", fase="No se pudo completar",
                           error=(str(exc).strip() or exc.__class__.__name__)[:300])
    finally:
        try:
            _SEMAFORO.release()
        except Exception:  # noqa: BLE001
            pass


def obtener(tid, uid=None):
    """Copia del trabajo para devolverla en JSON (None si no existe o no es tuyo)."""
    with _LOCK:
        t = _TRABAJOS.get(tid)
        if not t:
            return None
        if uid is not None and t["uid"] != uid:
            return None
        copia = dict(t)
        if copia["estado"] == "cola":
            delante = sum(1 for o in _TRABAJOS.values()
                          if o["id"] != tid and o["estado"] in ("cola", "procesando")
                          and o["creado"] <= copia["creado"])
            posicion = delante + 1
            copia["fase"] = (f"En cola — tu posición es {posicion}" if posicion > 1
                             else "Preparando tu turno...")
    return copia
