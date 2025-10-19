# academico.py
from flask import Blueprint, jsonify
from db import get_connection
from logger import log_event

academico_bp = Blueprint("academico", __name__)
SERVICE = "continental.edu.pe/soa/academico-service"

# ======================================================
# LISTAR CURSOS MATRICULADOS POR CICLO (CON CRÉDITOS)
# ======================================================
@academico_bp.route("/matriculas/<int:codigo_estudiante>", methods=["GET"])
def obtener_matriculas_por_ciclo(codigo_estudiante):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener datos del estudiante
        cursor.execute("""
            SELECT id, nombre, carrera FROM estudiantes WHERE codigo = %s
        """, (codigo_estudiante,))
        estudiante = cursor.fetchone()

        if not estudiante:
            log_event(SERVICE, "WARNING", "GET", f"Estudiante {codigo_estudiante} no encontrado")
            return jsonify({
                "status": "error",
                "message": f"Estudiante {codigo_estudiante} no encontrado"
            }), 404

        estudiante_id = estudiante["id"]

        # Obtener cursos matriculados con ciclo y créditos
        cursor.execute("""
            SELECT 
                c.nombre AS curso,
                c.ciclo,
                c.creditos
            FROM matriculas m
            JOIN cursos c ON m.curso_id = c.id
            WHERE m.estudiante_id = %s
            ORDER BY c.ciclo ASC
        """, (estudiante_id,))
        rows = cursor.fetchall()

        if not rows:
            return jsonify({
                "status": "success",
                "codigo_estudiante": codigo_estudiante,
                "nombre": estudiante["nombre"],
                "carrera": estudiante["carrera"],
                "matriculas": []
            }), 200

        # Agrupar por ciclo y calcular créditos totales
        ciclos = {}
        for row in rows:
            ciclo = row["ciclo"]
            if ciclo not in ciclos:
                ciclos[ciclo] = {"cursos": [], "total_creditos": 0}
            ciclos[ciclo]["cursos"].append(row["curso"])
            ciclos[ciclo]["total_creditos"] += row["creditos"]

        resultado = [
            {"ciclo": ciclo, "cursos": data["cursos"], "total_creditos": data["total_creditos"]}
            for ciclo, data in ciclos.items()
        ]

        log_event(SERVICE, "INFO", "GET", f"Historial académico recuperado {codigo_estudiante}")
        return jsonify({
            "status": "success",
            "codigo_estudiante": codigo_estudiante,
            "nombre": estudiante["nombre"],
            "carrera": estudiante["carrera"],
            "matriculas": resultado
        }), 200

    except Exception as e:
        log_event(SERVICE, "ERROR", "GET", f"Error al obtener historial académico: {e}")
        return jsonify({
            "status": "error",
            "message": "Error interno del servidor"
        }), 500
    finally:
        if conn:
            cursor.close()
            conn.close()
