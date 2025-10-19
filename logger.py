# logger.py
from db import get_connection
from datetime import datetime
from flask import request, g
import socket, time, logging, os, uuid

DOMAIN = "continental.edu.pe/soa"

# Archivo de logs
LOG_FILE = os.path.join(os.path.dirname(__file__), "soa_matricula.log")

# ---------- NUEVO: Formateador seguro ----------
class SafeFormatter(logging.Formatter):
    """Formatter que evita errores si faltan campos personalizados."""
    def format(self, record):
        for attr in ("service", "method", "request_id"):
            if not hasattr(record, attr):
                setattr(record, attr, "-")
        return super().format(record)


# ---------- Configuración de logging ----------
formatter = SafeFormatter(
    "%(asctime)s [%(levelname)s] [%(service)s] [%(method)s] [req:%(request_id)s] %(message)s",
    "%Y-%m-%d %H:%M:%S"
)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Handler para archivo
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

# Handler para consola
console = logging.StreamHandler()
console.setFormatter(formatter)
root_logger.addHandler(console)


# ---------- Funciones auxiliares ----------
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
    """Identificador único por transacción SOA"""
    rid = getattr(g, "request_id", None)
    if not rid:
        rid = str(uuid.uuid4())[:8]
        g.request_id = rid
    return rid


def log_event(servicio, categoria, operacion, mensaje, inicio=None, usuario=None):
    """
    servicio: 'matriculas-service'
    categoria: INFO | ERROR | WARNING
    operacion: GET | POST | PUT | DELETE | SERVICE
    mensaje: descripción del evento
    inicio: time.time() opcional
    """
    conn = None
    try:
        ip = _get_client_ip()
        usuario = usuario or _get_user()
        request_id = _get_request_id()
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        duracion = round(time.time() - inicio, 4) if inicio else None

        extra = {
            "service": f"{servicio}",
            "method": operacion,
            "request_id": request_id
        }

        logger = logging.getLogger(servicio)
        mensaje_fmt = f"{mensaje} | IP:{ip} | User:{usuario} | t:{duracion}s"

        # Registrar en archivo + consola
        if categoria == "INFO":
            logger.info(mensaje_fmt, extra=extra)
        elif categoria == "WARNING":
            logger.warning(mensaje_fmt, extra=extra)
        elif categoria == "ERROR":
            logger.error(mensaje_fmt, extra=extra)

        # Registrar en BD
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO logs (servicio, categoria, operacion, mensaje, fecha_hora, ip, usuario, duracion, request_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (f"{DOMAIN}/{servicio}", categoria, operacion, mensaje, fecha_hora, ip, usuario, duracion, request_id))
        conn.commit()

    except Exception as e:
        logging.getLogger("logger").error(f"[{DOMAIN}/logger][ERROR] Fallo al registrar log: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()
