from flask import Blueprint, render_template, request, jsonify
from db import get_connection
from datetime import datetime
from logger import log_event   # ✅ Importar el logger
import time                   # ✅ Para medir duración de ejecución

matriculas_bp = Blueprint('matriculas', __name__)

# ======================================================
# LISTAR MATRÍCULAS EN TABLA (para mostrar en la interfaz)
# ======================================================
@matriculas_bp.route("/listar", methods=["GET"])
def listar_matriculas():
    inicio = time.time()  # ⏱ Inicio para calcular duración
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                m.id, 
                e.nombre AS estudiante, 
                e.ciclo AS ciclo_estudiante,
                c.nombre AS curso, 
                m.fecha, 
                m.estado
            FROM matriculas m
            JOIN estudiantes e ON m.estudiante_id = e.id
            JOIN cursos c ON m.curso_id = c.id
            ORDER BY m.id DESC
        """)
        data = cursor.fetchall()

        # ✅ Registrar acción en el log
        log_event(
            servicio="matriculas-service",
            categoria="INFO",
            operacion="GET",
            mensaje="Listado de matrículas consultado correctamente",
            inicio=inicio
        )

        return jsonify(data)
    except Exception as e:
        print("❌ Error al listar matrículas:", e)
        # ✅ Registrar error en el log
        log_event(
            servicio="matriculas-service",
            categoria="ERROR",
            operacion="GET",
            mensaje=f"Error al listar matrículas: {str(e)}",
            inicio=inicio
        )
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


# ======================================================
# FORMULARIO HTML DE MATRÍCULAS
# ======================================================
@matriculas_bp.route("/html", methods=["GET"])
def matriculas_html():
    inicio = time.time()
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Traer todos los estudiantes
        cursor.execute("SELECT id, codigo, nombre, ciclo FROM estudiantes ORDER BY nombre ASC")
        estudiantes = cursor.fetchall()

        # Traer todos los cursos
        cursor.execute("SELECT id, codigo, nombre, creditos FROM cursos ORDER BY nombre ASC")
        cursos = cursor.fetchall()

        # ✅ Registrar vista HTML en el log
        log_event(
            servicio="matriculas-service",
            categoria="INFO",
            operacion="GET",
            mensaje="Formulario HTML de matrícula cargado correctamente",
            inicio=inicio
        )

        return render_template("matriculas.html", estudiantes=estudiantes, cursos=cursos)
    except Exception as e:
        print("❌ Error al cargar matrícula HTML:", e)
        # ✅ Registrar error en el log
        log_event(
            servicio="matriculas-service",
            categoria="ERROR",
            operacion="GET",
            mensaje=f"Error al cargar vista HTML de matrícula: {str(e)}",
            inicio=inicio
        )
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


# ======================================================
# REGISTRAR MATRÍCULA (VALIDA DUPLICADO)
# ======================================================
@matriculas_bp.route("/", methods=["POST"])
def registrar_matricula():
    inicio = time.time()  # ⏱ Inicio de operación
    try:
        data = request.get_json()
        estudiante_id = data.get("estudiante_id")
        curso_id = data.get("curso_id")

        if not estudiante_id or not curso_id:
            log_event(
                servicio="matriculas-service",
                categoria="WARNING",
                operacion="POST",
                mensaje="Intento de matrícula con datos incompletos",
                inicio=inicio
            )
            return jsonify({"status": "error", "message": "Faltan datos"}), 400

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Validar duplicado
        cursor.execute(
            "SELECT COUNT(*) AS existe FROM matriculas WHERE estudiante_id=%s AND curso_id=%s",
            (estudiante_id, curso_id)
        )
        if cursor.fetchone()["existe"] > 0:
            log_event(
                servicio="matriculas-service",
                categoria="WARNING",
                operacion="POST",
                mensaje=f"Matrícula duplicada detectada para estudiante {estudiante_id} y curso {curso_id}",
                inicio=inicio
            )
            return jsonify({"status": "error", "message": "Ya existe una matrícula con esos datos"}), 400

        # Insertar matrícula
        cursor.execute("""
            INSERT INTO matriculas (estudiante_id, curso_id, fecha, estado)
            VALUES (%s, %s, %s, %s)
        """, (estudiante_id, curso_id, datetime.now(), "activo"))
        conn.commit()

        # ✅ Registrar en el log el éxito
        log_event(
            servicio="matriculas-service",
            categoria="INFO",
            operacion="POST",
            mensaje=f"Se matriculó correctamente al estudiante ID {estudiante_id} en el curso ID {curso_id}",
            inicio=inicio
        )

        return jsonify({"status": "success", "message": "Matrícula registrada correctamente"}), 201
    except Exception as e:
        print("❌ Error al registrar matrícula:", e)
        # ✅ Registrar error en el log
        log_event(
            servicio="matriculas-service",
            categoria="ERROR",
            operacion="POST",
            mensaje=f"Error al registrar matrícula: {str(e)}",
            inicio=inicio
        )
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass
