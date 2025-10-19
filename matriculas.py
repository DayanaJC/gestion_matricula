# matriculas.py
from flask import Blueprint, request, jsonify
from db import get_connection
from logger import log_event
import requests, time

# ======================================================
# CONFIGURACIÓN BASE
# ======================================================
matriculas_bp = Blueprint("matriculas", __name__)
SERVICE = "continental.edu.pe/soa/matriculas-service"

# Rutas correctas según tu app.py
SERVICIO_ESTUDIANTES = "http://127.0.0.1:5000/api/v1/continental.edu.pe/soa/estudiantes-service/"
SERVICIO_CURSOS = "http://127.0.0.1:5000/api/v1/continental.edu.pe/soa/cursos-service/"

# ======================================================
# LISTAR TODAS LAS MATRÍCULAS (GET)
# ======================================================
@matriculas_bp.route("/", methods=["GET"])
def get_matriculas():
    inicio = time.time()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                m.id,
                e.codigo AS codigo_estudiante,
                e.nombre AS estudiante,
                c.codigo AS codigo_curso,
                c.nombre AS curso,
                m.fecha,
                m.estado
            FROM matriculas m
            JOIN estudiantes e ON m.estudiante_id = e.id
            JOIN cursos c ON m.curso_id = c.id
            ORDER BY m.id ASC
        """)
        data = cursor.fetchall()

        log_event(SERVICE, "INFO", "GET", f"{len(data)} matrículas listadas", inicio)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as e:
        log_event(SERVICE, "ERROR", "GET", f"Error al listar matrículas: {e}", inicio)
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

# ======================================================
# REGISTRAR NUEVA MATRÍCULA (POST)
# ======================================================
@matriculas_bp.route("/", methods=["POST"])
def add_matricula():
    inicio = time.time()
    datos = request.get_json() or {}
    codigo_estudiante = datos.get("codigo_estudiante")
    codigo_curso = datos.get("codigo_curso")

    if not codigo_estudiante or not codigo_curso:
        log_event(SERVICE, "WARNING", "POST",
                    "Faltan datos: código_estudiante o código_curso", inicio)
        return jsonify({
            "status": "error",
            "message": "Faltan datos obligatorios: código_estudiante o código_curso"
        }), 400

    try:
        # ===== Validar existencia de estudiante =====
        url_est = f"{SERVICIO_ESTUDIANTES}/codigo/{codigo_estudiante}"
        resp_est = requests.get(url_est, timeout=5)
        if resp_est.status_code != 200:
            log_event(SERVICE, "WARNING", "POST",
                        f"Estudiante {codigo_estudiante} no encontrado en {url_est}", inicio)
            return jsonify({
                "status": "error",
                "message": f"Estudiante {codigo_estudiante} no encontrado"
            }), 404

        # ===== Validar existencia de curso =====
        url_cur = f"{SERVICIO_CURSOS}/codigo/{codigo_curso}"
        resp_cur = requests.get(url_cur, timeout=5)
        if resp_cur.status_code != 200:
            log_event(SERVICE, "WARNING", "POST",
                        f"Curso {codigo_curso} no encontrado en {url_cur}", inicio)
            return jsonify({
                "status": "error",
                "message": f"Curso {codigo_curso} no encontrado"
            }), 404

        # ===== Extraer correctamente los datos (usa .get("data") o raíz) =====
        estudiante_json = resp_est.json()
        curso_json = resp_cur.json()

        estudiante_data = estudiante_json.get("data", estudiante_json)
        curso_data = curso_json.get("data", curso_json)

        est_id = estudiante_data.get("id")
        cur_id = curso_data.get("id")

        if not est_id or not cur_id:
            log_event(SERVICE, "ERROR", "POST",
                        f"Datos inválidos: est_id={est_id}, cur_id={cur_id}", inicio)
            return jsonify({
                "status": "error",
                "message": "Error en estructura de datos de servicios externos"
            }), 500

        # ===== Validar duplicado =====
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM matriculas
            WHERE estudiante_id=%s AND curso_id=%s
        """, (est_id, cur_id))
        if cursor.fetchone()[0] > 0:
            log_event(SERVICE, "WARNING", "POST",
                        f"Duplicado: estudiante {codigo_estudiante} ya matriculado en curso {codigo_curso}", inicio)
            return jsonify({
                "status": "error",
                "message": "Matrícula duplicada"
            }), 400

        # ===== Insertar matrícula =====
        cursor.execute("""
            INSERT INTO matriculas (estudiante_id, curso_id, estado)
            VALUES (%s, %s, 'activo')
        """, (est_id, cur_id))
        conn.commit()

        log_event(SERVICE, "INFO", "POST",
                    f"Matrícula creada correctamente: estudiante {codigo_estudiante}, curso {codigo_curso}", inicio)
        return jsonify({
            "status": "success",
            "message": "Matrícula registrada correctamente"
        }), 201

    except requests.exceptions.RequestException as e:
        log_event(SERVICE, "ERROR", "POST",
                    f"Fallo de comunicación con servicios externos: {e}", inicio)
        return jsonify({
            "status": "error",
            "message": "Error de comunicación con servicios externos"
        }), 500
    except Exception as e:
        log_event(SERVICE, "ERROR", "POST",
                    f"Error general al registrar matrícula: {e}", inicio)
        return jsonify({
            "status": "error",
            "message": f"Error general al registrar matrícula: {str(e)}"
        }), 500
    finally:
        if 'conn' in locals() and conn:
            cursor.close()
            conn.close()
