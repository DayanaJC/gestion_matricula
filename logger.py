# logger.py
from db import get_connection
from datetime import datetime
from flask import request, g
import socket, time, logging, os, uuid

DOMAIN = "continental.edu.pe/soa"
LOG_FILE = os.path.join(os.path.dirname(__file__), "soa_matricula.log")

# ==========================================================
# FORMATEADOR SEGURO
# ==========================================================
class SafeFormatter(logging.Formatter):
    """Evita errores si faltan campos personalizados."""
    def format(self, record):
        for attr in ("service", "method", "request_id"):
            if not hasattr(record, attr):
                setattr(record, attr, "-")
        return super().format(record)

formatter = SafeFormatter(
    "%(asctime)s [%(levelname)s] [%(service)s] [%(method)s] [req:%(request_id)s] %(message)s",
    "%Y-%m-%d %H:%M:%S"
)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Archivo
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

# Consola
console = logging.StreamHandler()
console.setFormatter(formatter)
root_logger.addHandler(console)

# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================
def _get_client_ip():
    try:
        return request.headers.get("X-Forwarded-For", request.remote_addr)
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "unknown"

def _get_user():
    try:
        return request.headers.get("X-User") or "anon"
    except Exception:
        return "anon"

def _get_request_id():
    rid = getattr(g, "request_id", None)
    if not rid:
        rid = str(uuid.uuid4())[:8]
        g.request_id = rid
    return rid

# ==========================================================
# REGISTRO DE EVENTOS
# ==========================================================
def log_event(servicio, categoria, operacion, mensaje, inicio=None, usuario=None):
    """
    servicio: 'matriculas-service'
    categoria: INFO | ERROR | WARNING
    operacion: GET | POST | PUT | DELETE | SERVICE
    """
    conn = None
    cur = None
    try:
        ip = _get_client_ip()
        usuario = usuario or _get_user()
        request_id = _get_request_id()
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        duracion = round(time.time() - inicio, 4) if inicio else None

        extra = {"service": servicio, "method": operacion, "request_id": request_id}
        mensaje_fmt = f"{mensaje} | IP:{ip} | User:{usuario} | t:{duracion}s"

        logger = logging.getLogger(servicio)

        if categoria == "INFO":
            logger.info(mensaje_fmt, extra=extra)
        elif categoria == "WARNING":
            logger.warning(mensaje_fmt, extra=extra)
        elif categoria == "ERROR":
            logger.error(mensaje_fmt, extra=extra)

        # Guarda también en la BD
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO logs (servicio, categoria, operacion, mensaje, fecha_hora, ip, usuario, duracion, request_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (f"{DOMAIN}/{servicio}", categoria, operacion, mensaje, fecha_hora, ip, usuario, duracion, request_id))
        conn.commit()

    except Exception as e:
            print(f"⚠️ ERROR LOGGER: {e}")
            logging.getLogger("logger").error(f"[{DOMAIN}/logger][ERROR] Fallo al registrar log: {e}")
    finally:
        if cur: cur.close()
        if conn: conn.close()

# ==========================================================
# INIT PARA TRAZABILIDAD
# ==========================================================
def init_request_tracing():
    """Inicializa un identificador único por request"""
    g.request_id = str(uuid.uuid4())[:8]
    g.start_time = time.time()