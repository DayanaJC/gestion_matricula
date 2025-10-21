# estudiantes.py
from flask import Blueprint, request, jsonify
from db import get_connection
from logger import log_event
import time

# ======================================================
# CONFIGURACIÓN BASE
# ======================================================
estudiantes_bp = Blueprint("estudiantes", __name__)
SERVICE = "continental.edu.pe/soa/estudiantes-service"

# ======================================================
# LISTAR ESTUDIANTES (GET)
# ======================================================
@estudiantes_bp.route("/", methods=["GET"])
def listar_estudiantes():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM estudiantes")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"status": "success", "data": data})

# ======================================================
# CONSULTAR POR CÓDIGO (GET)
# ======================================================
@estudiantes_bp.route("/codigo/<string:codigo>", methods=["GET"])
def get_estudiante_por_codigo(codigo):
    inicio = time.time()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, codigo, nombre, carrera, ciclo, correo, estado
            FROM estudiantes
            WHERE codigo =%s
        """, (codigo,))
        est = cursor.fetchone()

        if not est:
            log_event(SERVICE, "WARNING", "GET",
                        f"Estudiante {codigo} no encontrado", inicio)
            return jsonify({"status": "error", "message": "Estudiante no encontrado"}), 404

        log_event(SERVICE, "INFO", "GET",
                    f"Consulta de estudiante {codigo} exitosa", inicio)
        return jsonify({"status": "success", "data": est}), 200
    except Exception as e:
        log_event(SERVICE, "ERROR", "GET",
                    f"Error al consultar estudiante {codigo}: {e}", inicio)
        return jsonify({"status": "error", "message": "Error en búsqueda por código"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

# ======================================================
# REGISTRAR ESTUDIANTE (POST)
# ======================================================
@estudiantes_bp.route("/", methods=["POST"])
def agregar_estudiante():
    inicio = time.time()
    data = request.get_json() or {}
    codigo = data.get("codigo")
    nombre = data.get("nombre")
    correo = data.get("correo")
    carrera = data.get("carrera")
    ciclo = data.get("ciclo")
    estado = data.get("estado", "activo")

    # Validación de campos requeridos
    if not all([codigo, nombre, correo, carrera, ciclo]):
        log_event(SERVICE, "WARNING", "POST",
                    "Campos obligatorios faltantes", inicio)
        return jsonify({"status": "error", "message": "Faltan datos obligatorios"}), 400

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Validar duplicado de código
        cursor.execute("SELECT COUNT(*) FROM estudiantes WHERE codigo=%s", (codigo,))
        if cursor.fetchone()[0] > 0:
            log_event(SERVICE, "WARNING", "POST",
                        f"Código duplicado: {codigo}", inicio)
            return jsonify({"status": "error", "message": f"Código duplicado: {codigo}"}), 400

        cursor.execute("""
            INSERT INTO estudiantes (codigo, nombre, correo, carrera, ciclo, estado)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (codigo, nombre, correo, carrera, ciclo, estado))
        conn.commit()

        log_event(SERVICE, "INFO", "POST",
                    f"Estudiante {nombre} ({codigo}) registrado correctamente", inicio)
        return jsonify({"status": "success", "message": "Estudiante registrado correctamente"}), 201
    except Exception as e:
        log_event(SERVICE, "ERROR", "POST",
                    f"Fallo al registrar estudiante {codigo}: {e}", inicio)
        return jsonify({"status": "error", "message": f"Error al registrar estudiante: {e}"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

# ======================================================
# ACTUALIZAR ESTUDIANTE (PUT)
# ======================================================
@estudiantes_bp.route("/<int:id>", methods=["PUT"])
def update_estudiante(id):
    inicio = time.time()
    data = request.get_json() or {}

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM estudiantes WHERE id=%s", (id,))
    estudiante = cursor.fetchone()

    if not estudiante:
        log_event(SERVICE, "WARNING", "PUT",
                    f"Estudiante ID {id} no encontrado", inicio)
        return jsonify({"status": "error", "message": "Estudiante no encontrado"}), 404

    codigo = data.get("codigo", estudiante["codigo"])
    nombre = data.get("nombre", estudiante["nombre"])
    correo = data.get("correo", estudiante["correo"])
    carrera = data.get("carrera", estudiante["carrera"])
    ciclo = data.get("ciclo", estudiante["ciclo"])
    estado = data.get("estado", estudiante["estado"])

    try:
        cursor.execute("""
            UPDATE estudiantes 
            SET codigo=%s, nombre=%s, correo=%s, carrera=%s, ciclo=%s, estado=%s
            WHERE id=%s
        """, (codigo, nombre, correo, carrera, ciclo, estado, id))
        conn.commit()

        log_event(SERVICE, "INFO", "PUT",
                    f"Estudiante {codigo} actualizado correctamente", inicio)
        return jsonify({"status": "success", "message": "Estudiante actualizado correctamente"}), 200
    except Exception as e:
        log_event(SERVICE, "ERROR", "PUT",
                    f"Error al actualizar estudiante {codigo}: {e}", inicio)
        return jsonify({"status": "error", "message": "Error al actualizar estudiante"}), 500
    finally:
        cursor.close()
        conn.close()

# ======================================================
# ELIMINAR ESTUDIANTE (DELETE)
# ======================================================
@estudiantes_bp.route("/<int:id>", methods=["DELETE"])
def delete_estudiante(id):
    inicio = time.time()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM estudiantes WHERE id=%s", (id,))
        conn.commit()

        if cursor.rowcount == 0:
            log_event(SERVICE, "WARNING", "DELETE",
                        f"Estudiante ID {id} no encontrado", inicio)
            return jsonify({"status": "error", "message": "Estudiante no encontrado"}), 404

        log_event(SERVICE, "INFO", "DELETE",
                        f"Estudiante ID {id} eliminado correctamente", inicio)
        return jsonify({"status": "success", "message": "Estudiante eliminado correctamente"}), 200
    except Exception as e:
        log_event(SERVICE, "ERROR", "DELETE",
                        f"Error al eliminar estudiante {id}: {e}", inicio)
        return jsonify({"status": "error", "message": "Error al eliminar estudiante"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()
