# cursos.py
from flask import Blueprint, request, jsonify
from db import get_connection
from logger import log_event
import time

# ======================================================
# CONFIGURACIÓN BASE
# ======================================================
cursos_bp = Blueprint("cursos", __name__)
SERVICE = "continental.edu.pe/soa/cursos-service"

# ======================================================
# LISTAR CURSOS (GET)
# ======================================================
@cursos_bp.route("/", methods=["GET"])
def get_cursos():
    inicio = time.time()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, codigo, nombre, creditos, ciclo
            FROM cursos
            ORDER BY id ASC
        """)
        rows = cursor.fetchall()

        log_event(SERVICE, "INFO", "GET",
                    f"Listado de {len(rows)} cursos recuperado correctamente", inicio)
        return jsonify({"status": "success", "data": rows}), 200
    except Exception as e:
        log_event(SERVICE, "ERROR", "GET",
                    f"Error al listar cursos: {e}", inicio)
        return jsonify({"status": "error", "message": "Error al obtener cursos"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

# ======================================================
# OBTENER CURSO POR CÓDIGO (GET)
# ======================================================
@cursos_bp.route("/codigo/<string:codigo>", methods=["GET"])
def get_curso_por_codigo(codigo):
    inicio = time.time()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, codigo, nombre, creditos, ciclo
            FROM cursos
            WHERE codigo=%s
        """, (codigo,))
        curso = cursor.fetchone()

        if not curso:
            log_event(SERVICE, "WARNING", "GET",
                        f"Curso {codigo} no encontrado", inicio)
            return jsonify({"status": "error", "message": "Curso no encontrado"}), 404

        log_event(SERVICE, "INFO", "GET",
                    f"Consulta de curso {codigo} exitosa", inicio)
        return jsonify({"status": "success", "data": curso}), 200
    except Exception as e:
        log_event(SERVICE, "ERROR", "GET",
                    f"Error al consultar curso {codigo}: {e}", inicio)
        return jsonify({"status": "error", "message": "Error al obtener curso"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

# ======================================================
# CREAR NUEVO CURSO (POST)
# ======================================================
@cursos_bp.route("/", methods=["POST"])
def create_curso():
    inicio = time.time()
    data = request.get_json() or {}
    nombre = data.get("nombre")
    codigo = data.get("codigo")
    creditos = data.get("creditos")
    ciclo = data.get("ciclo")

    # Validaciones de campos
    if not all([nombre, codigo, creditos, ciclo]):
        log_event(SERVICE, "WARNING", "POST",
                    "Campos obligatorios faltantes", inicio)
        return jsonify({"status": "error", "message": "Faltan campos obligatorios"}), 400

    try:
        creditos = int(creditos)
    except ValueError:
        log_event(SERVICE, "WARNING", "POST",
                    f"Créditos inválidos para curso {codigo}", inicio)
        return jsonify({"status": "error", "message": "Créditos inválidos"}), 400

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Validar duplicado de código
        cursor.execute("SELECT COUNT(*) FROM cursos WHERE codigo=%s", (codigo,))
        if cursor.fetchone()[0] > 0:
            log_event(SERVICE, "WARNING", "POST",
                        f"Código duplicado: {codigo}", inicio)
            return jsonify({"status": "error", "message": f"Código duplicado: {codigo}"}), 400

        cursor.execute("""
            INSERT INTO cursos (nombre, codigo, creditos, ciclo)
            VALUES (%s, %s, %s, %s)
        """, (nombre, codigo, creditos, ciclo))
        conn.commit()

        log_event(SERVICE, "INFO", "POST",
                    f"Nuevo curso {codigo} - {nombre} registrado correctamente", inicio)
        return jsonify({"status": "success", "message": "Curso creado correctamente"}), 201
    except Exception as e:
        log_event(SERVICE, "ERROR", "POST",
                    f"Error al crear curso {codigo}: {e}", inicio)
        return jsonify({"status": "error", "message": "Error al crear curso"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

# ======================================================
# ACTUALIZAR CURSO (PUT)
# ======================================================
@cursos_bp.route("/<int:id>", methods=["PUT"])
def update_curso(id):
    inicio = time.time()
    data = request.get_json() or {}
    nombre = data.get("nombre")
    codigo = data.get("codigo")
    creditos = data.get("creditos")
    ciclo = data.get("ciclo")

    if not all([nombre, codigo, creditos, ciclo]):
        log_event(SERVICE, "WARNING", "PUT",
                    "Campos obligatorios faltantes para actualización", inicio)
        return jsonify({"status": "error", "message": "Faltan campos"}), 400

    try:
        creditos = int(creditos)
    except ValueError:
        log_event(SERVICE, "WARNING", "PUT",
                    f"Créditos inválidos en actualización de curso {codigo}", inicio)
        return jsonify({"status": "error", "message": "Créditos inválidos"}), 400

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE cursos
            SET nombre=%s, codigo=%s, creditos=%s, ciclo=%s
            WHERE id=%s
        """, (nombre, codigo, creditos, ciclo, id))
        conn.commit()

        if cursor.rowcount == 0:
            log_event(SERVICE, "WARNING", "PUT",
                        f"Curso ID {id} no encontrado para actualización", inicio)
            return jsonify({"status": "error", "message": "Curso no encontrado"}), 404

        log_event(SERVICE, "INFO", "PUT",
                        f"Curso {codigo} actualizado correctamente", inicio)
        return jsonify({"status": "success", "message": "Curso actualizado correctamente"}), 200
    except Exception as e:
        log_event(SERVICE, "ERROR", "PUT",
                    f"Error al actualizar curso ID {id}: {e}", inicio)
        return jsonify({"status": "error", "message": "Error al actualizar curso"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

# ======================================================
# ELIMINAR CURSO (DELETE)
# ======================================================
@cursos_bp.route("/<int:id>", methods=["DELETE"])
def delete_curso(id):
    inicio = time.time()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cursos WHERE id=%s", (id,))
        conn.commit()

        if cursor.rowcount == 0:
            log_event(SERVICE, "WARNING", "DELETE",
                        f"Curso ID {id} no encontrado", inicio)
            return jsonify({"status": "error", "message": "Curso no encontrado"}), 404

        log_event(SERVICE, "INFO", "DELETE",
                    f"Curso ID {id} eliminado correctamente", inicio)
        return jsonify({"status": "success", "message": "Curso eliminado correctamente"}), 200
    except Exception as e:
        log_event(SERVICE, "ERROR", "DELETE",
                    f"Error al eliminar curso ID {id}: {e}", inicio)
        return jsonify({"status": "error", "message": "Error al eliminar curso"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

