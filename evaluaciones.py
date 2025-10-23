# evaluaciones.py
from flask import Blueprint, request, jsonify, render_template
from db import get_connection
from logger import log_event
import time

evaluaciones_bp = Blueprint("evaluaciones", __name__)
SERVICE = "continental.edu.pe/soa/evaluaciones-service"

# ===========================
# LISTAR EVALUACIONES (GET)
# ===========================
@evaluaciones_bp.route("/", methods=["GET"])
def listar_evaluaciones():
    inicio = time.time()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT e.id AS id_estudiante, e.nombre AS estudiante,
                   c.id AS id_curso, c.nombre AS curso,
                   ev.nota
            FROM evaluaciones ev
            JOIN estudiantes e ON ev.id_estudiante = e.id
            JOIN cursos c ON ev.id_curso = c.id
        """)
        data = cursor.fetchall()

        log_event(SERVICE, "INFO", "GET", "Listado de evaluaciones obtenido", inicio)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as e:
        log_event(SERVICE, "ERROR", "GET", f"Error al listar evaluaciones: {e}", inicio)
        return jsonify({"status": "error", "message": "Error al listar evaluaciones"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

# ===========================
# LISTAR CURSOS MATRICULADOS DE UN ESTUDIANTE
# ===========================
@evaluaciones_bp.route("/cursos/<string:codigo_estudiante>", methods=["GET"])
def cursos_matriculados(codigo_estudiante):
    inicio = time.time()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT curso, codigo_curso 
            FROM vista_matriculas
            WHERE codigo_estudiante=%s
        """, (codigo_estudiante,))
        cursos = cursor.fetchall()

        log_event(SERVICE, "INFO", "GET", f"Cursos matriculados de {codigo_estudiante}", inicio)
        return jsonify({"status": "success", "data": cursos}), 200
    except Exception as e:
        log_event(SERVICE, "ERROR", "GET", f"Error al obtener cursos: {e}", inicio)
        return jsonify({"status": "error", "message": "Error al obtener cursos"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

# ===========================
# AGREGAR EVALUACIÓN (POST)
# ===========================
@evaluaciones_bp.route("/", methods=["POST"])
def agregar_evaluacion():
    inicio = time.time()
    data = request.get_json() or {}
    codigo_estudiante = data.get("codigo_estudiante")
    codigo_curso = data.get("codigo_curso")
    nota = data.get("nota")

    if not all([codigo_estudiante, codigo_curso, nota]):
        log_event(SERVICE, "WARNING", "POST", "Datos incompletos para evaluación", inicio)
        return jsonify({"status": "error", "message": "Faltan datos obligatorios"}), 400

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Insertar evaluación usando IDs reales
        cursor.execute("""
            INSERT INTO evaluaciones (id_estudiante, id_curso, nota)
            VALUES (
                (SELECT id FROM estudiantes WHERE codigo=%s),
                (SELECT id FROM cursos WHERE codigo=%s),
                %s
            )
        """, (codigo_estudiante, codigo_curso, nota))
        conn.commit()

        log_event(SERVICE, "INFO", "POST", f"Evaluación registrada: {codigo_estudiante} - {codigo_curso}", inicio)
        return jsonify({"status": "success", "message": "Evaluación registrada correctamente"}), 201
    except Exception as e:
        log_event(SERVICE, "ERROR", "POST", f"Error al registrar evaluación: {e}", inicio)
        return jsonify({"status": "error", "message": f"Error al registrar evaluación: {e}"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()
