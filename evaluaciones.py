# evaluaciones.py
from flask import Blueprint, request, jsonify
from db import get_connection
from logger import log_event
import requests, time

# ======================================================
evaluaciones_bp = Blueprint("evaluaciones", __name__)
SERVICE = "continental.edu.pe/soa/evaluaciones-service"

SERVICIO_ESTUDIANTES = "http://127.0.0.1:5000/api/v1/continental.edu.pe/soa/estudiantes-service"
SERVICIO_CURSOS = "http://127.0.0.1:5000/api/v1/continental.edu.pe/soa/cursos-service"
SERVICIO_MATRICULAS = "http://127.0.0.1:5000/api/v1/continental.edu.pe/soa/matriculas-service"

# helper para siguiente ciclo
CICLOS = ["I","II","III","IV","V","VI","VII","VIII","IX","X"]

def siguiente_ciclo(ciclo_actual):
    try:
        idx = CICLOS.index(ciclo_actual)
        if idx < len(CICLOS) - 1:
            return CICLOS[idx + 1]
    except ValueError:
        pass
    return ciclo_actual  # si no se reconoce, mantener

def puede_promover(estudiante_id, ciclo_actual):
    """
    Verifica que todos los cursos del estudiante en ciclo_actual
    estén aprobados (nota >= 11).
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # obtener todas las matrículas del estudiante para cursos del ciclo_actual
        cur.execute("""
            SELECT m.id AS matricula_id, c.id AS curso_id
            FROM matriculas m
            JOIN cursos c ON m.curso_id = c.id
            WHERE m.estudiante_id = %s AND c.ciclo = %s
        """, (estudiante_id, ciclo_actual))
        filas = cur.fetchall()
        if not filas:
            return False  # si no está matriculado en cursos de ese ciclo, no promovemos

        # por cada curso verificar si tiene evaluación aprobatoria
        for f in filas:
            cur.execute("""
                SELECT nota FROM evaluaciones
                WHERE estudiante_id = %s AND curso_id = %s
                ORDER BY fecha DESC LIMIT 1
            """, (estudiante_id, f["curso_id"]))
            ev = cur.fetchone()
            if not ev or ev.get("nota", 0) < 11:
                return False
        return True
    finally:
        cur.close()
        conn.close()

# =========================
# LISTAR EVALUACIONES (GET)
# =========================
@evaluaciones_bp.route("/", methods=["GET"])
def get_evaluaciones():
    inicio = time.time()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                ev.id,
                e.codigo AS codigo_estudiante,
                e.nombre AS estudiante,
                c.codigo AS codigo_curso,
                c.nombre AS curso,
                ev.nota,
                ev.fecha
            FROM evaluaciones ev
            JOIN estudiantes e ON ev.estudiante_id = e.id
            JOIN cursos c ON ev.curso_id = c.id
            ORDER BY ev.id ASC
        """)
        data = cursor.fetchall()
        log_event(SERVICE, "INFO", "GET", f"{len(data)} evaluaciones listadas", inicio)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as e:
        log_event(SERVICE, "ERROR", "GET", f"Error al listar evaluaciones: {e}", inicio)
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

# =========================
# AGREGAR EVALUACIÓN (POST)
# =========================
@evaluaciones_bp.route("/", methods=["POST"])
def add_evaluacion():
    inicio = time.time()
    datos = request.get_json() or {}
    codigo_estudiante = datos.get("codigo_estudiante")
    codigo_curso = datos.get("codigo_curso")
    nota = datos.get("nota")

    if not codigo_estudiante or not codigo_curso or nota is None:
        log_event(SERVICE, "WARNING", "POST", "Datos incompletos para registrar evaluación", inicio)
        return jsonify({"status": "error", "message": "Faltan datos obligatorios"}), 400

    try:
        nota = float(nota)
        if nota < 0 or nota > 20:
            return jsonify({"status": "error", "message": "Nota fuera de rango (0-20)"}), 400
    except:
        return jsonify({"status": "error", "message": "Nota inválida"}), 400

    try:
        # Validar existencia estudiante y curso
        est_resp = requests.get(f"{SERVICIO_ESTUDIANTES}/codigo/{codigo_estudiante}", timeout=5)
        cur_resp = requests.get(f"{SERVICIO_CURSOS}/codigo/{codigo_curso}", timeout=5)

        if est_resp.status_code != 200:
            return jsonify({"status": "error", "message": f"Estudiante {codigo_estudiante} no encontrado"}), 404
        if cur_resp.status_code != 200:
            return jsonify({"status": "error", "message": f"Curso {codigo_curso} no encontrado"}), 404

        est_data = est_resp.json().get("data", est_resp.json())
        cur_data = cur_resp.json().get("data", cur_resp.json())

        est_id = est_data.get("id")
        cur_id = cur_data.get("id")

        if not est_id or not cur_id:
            return jsonify({"status": "error", "message": "Datos inválidos desde servicios externos"}), 500

        # Verificar que el estudiante esté matriculado en ese curso (evita insertar evaluaciones no matriculadas)
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id FROM matriculas WHERE estudiante_id=%s AND curso_id=%s
        """, (est_id, cur_id))
        mat = cursor.fetchone()
        if not mat:
            return jsonify({"status": "error", "message": "El estudiante no está matriculado en ese curso"}), 400

        # Insertar/Registrar evaluación (permitimos múltiples evaluaciones, tomamos la última para aprobación)
        cursor.execute("""
            INSERT INTO evaluaciones (estudiante_id, curso_id, nota)
            VALUES (%s, %s, %s)
        """, (est_id, cur_id, nota))
        conn.commit()

        log_event(SERVICE, "INFO", "POST",
                    f"Evaluación registrada estudiante {codigo_estudiante}, curso {codigo_curso}, nota {nota}", inicio)

        # Después de registrar, verificar promoción
        estudiante_ciclo = est_data.get("ciclo")
        try:
            if puede_promover(est_id, estudiante_ciclo):
                nuevo = siguiente_ciclo(estudiante_ciclo)
                if nuevo != estudiante_ciclo:
                    cursor.execute("UPDATE estudiantes SET ciclo=%s WHERE id=%s", (nuevo, est_id))
                    conn.commit()
                    log_event(SERVICE, "INFO", "SERVICE",
                              f"Estudiante {codigo_estudiante} promovido {estudiante_ciclo} -> {nuevo}", inicio)
        except Exception as e_prom:
            # no impedir el registro si falla la verificación de promoción
            log_event(SERVICE, "ERROR", "SERVICE", f"Error al verificar/promover: {e_prom}", inicio)

        return jsonify({"status": "success", "message": "Evaluación registrada correctamente"}), 201

    except requests.exceptions.RequestException as e:
        log_event(SERVICE, "ERROR", "POST", f"Error comunicando con servicios externos: {e}", inicio)
        return jsonify({"status": "error", "message": "Error de comunicación con servicios externos"}), 500
    except Exception as e:
        log_event(SERVICE, "ERROR", "POST", f"Error general al registrar evaluación: {e}", inicio)
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'conn' in locals() and conn:
            cursor.close()
            conn.close()

# =========================
# ACTUALIZAR NOTA (PUT)
# =========================
@evaluaciones_bp.route("/<int:id>", methods=["PUT"])
def update_evaluacion(id):
    inicio = time.time()
    datos = request.get_json() or {}
    nota = datos.get("nota")

    if nota is None:
        return jsonify({"status": "error", "message": "Falta el campo nota"}), 400

    try:
        nota = float(nota)
        if nota < 0 or nota > 20:
            return jsonify({"status": "error", "message": "Nota fuera de rango (0-20)"}), 400
    except:
        return jsonify({"status": "error", "message": "Nota inválida"}), 400

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # obtener ids (estudiante_id, curso_id) antes de actualizar para poder verificar promoción
        cursor.execute("SELECT estudiante_id, curso_id FROM evaluaciones WHERE id=%s", (id,))
        ev_old = cursor.fetchone()
        if not ev_old:
            return jsonify({"status": "error", "message": "Evaluación no encontrada"}), 404

        cursor.execute("UPDATE evaluaciones SET nota=%s WHERE id=%s", (nota, id))
        conn.commit()

        log_event(SERVICE, "INFO", "PUT", f"Evaluación {id} actualizada a nota {nota}", inicio)

        # verificar promoción si corresponde (usar datos del estudiante)
        est_id = ev_old["estudiante_id"]
        cursor.execute("SELECT ciclo, codigo FROM estudiantes WHERE id=%s", (est_id,))
        est = cursor.fetchone()
        if est:
            estudiante_ciclo = est["ciclo"]
            if puede_promover(est_id, estudiante_ciclo):
                nuevo = siguiente_ciclo(estudiante_ciclo)
                if nuevo != estudiante_ciclo:
                    cursor.execute("UPDATE estudiantes SET ciclo=%s WHERE id=%s", (nuevo, est_id))
                    conn.commit()
                    log_event(SERVICE, "INFO", "SERVICE",
                              f"Estudiante {est.get('codigo','?')} promovido {estudiante_ciclo} -> {nuevo}", inicio)

        return jsonify({"status": "success", "message": "Evaluación actualizada correctamente"}), 200
    except Exception as e:
        log_event(SERVICE, "ERROR", "PUT", f"Error al actualizar evaluación: {e}", inicio)
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

# =========================
# RESUMEN DEL PROGRESO (GET)
# =========================
@evaluaciones_bp.route("/resumen/<int:codigo_estudiante>", methods=["GET"])
def resumen_estudiante(codigo_estudiante):
    inicio = time.time()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM estudiantes WHERE codigo=%s", (codigo_estudiante,))
        estudiante = cursor.fetchone()
        if not estudiante:
            return jsonify({"status": "error", "message": "Estudiante no encontrado"}), 404

        cursor.execute("""
            SELECT 
                c.nombre AS curso,
                c.ciclo,
                c.codigo AS codigo_curso,
                m.estado,
                COALESCE(ev.nota, 'Sin nota') AS nota
            FROM matriculas m
            JOIN cursos c ON m.curso_id = c.id
            LEFT JOIN evaluaciones ev 
                ON ev.estudiante_id = m.estudiante_id AND ev.curso_id = m.curso_id
            WHERE m.estudiante_id = %s
            ORDER BY c.ciclo, c.nombre
        """, (estudiante["id"],))

        progreso = cursor.fetchall()

        resumen = {
            "status": "success",
            "codigo_estudiante": codigo_estudiante,
            "nombre": estudiante["nombre"],
            "carrera": estudiante["carrera"],
            "ciclo_actual": estudiante["ciclo"],
            "estado": estudiante["estado"],
            "progreso_academico": progreso
        }

        log_event(SERVICE, "INFO", "GET", f"Resumen académico de estudiante {codigo_estudiante}", inicio)
        return jsonify(resumen), 200
    except Exception as e:
        log_event(SERVICE, "ERROR", "GET", f"Error al obtener resumen académico: {e}", inicio)
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()
