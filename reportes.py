# reportes.py
from flask import Blueprint, render_template, request
from db import get_connection

reportes_bp = Blueprint("reportes", __name__)

# =====================================================
# Página principal de Reportes
# =====================================================
@reportes_bp.route("/reporte_evaluaciones", methods=["GET", "POST"])
def reporte_evaluaciones():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 🔹 Obtener lista de alumnos para el selector
    cursor.execute("SELECT id, nombre FROM estudiantes")
    alumnos = cursor.fetchall()

    notas = []
    mensaje = ""
    alumno_seleccionado = None
    opcion = request.form.get("opcion")

    if request.method == "POST":
        alumno_id = request.form.get("alumno_id")
        opcion = request.form.get("opcion")
        alumno_seleccionado = alumno_id

        if opcion == "3_ultimos":
            query = """
            SELECT c.nombre AS curso, c.codigo, e.nota, m.ciclo
            FROM evaluaciones e
            JOIN matriculas m ON e.matricula_id = m.id
            JOIN cursos c ON m.curso_id = c.id
            WHERE m.estudiante_id = %s
            ORDER BY m.ciclo DESC
            LIMIT 3;
            """
        elif opcion == "ultimo":
            query = """
            SELECT c.nombre AS curso, c.codigo, e.nota, m.ciclo
            FROM evaluaciones e
            JOIN matriculas m ON e.matricula_id = m.id
            JOIN cursos c ON m.curso_id = c.id
            WHERE m.estudiante_id = %s
            ORDER BY m.ciclo DESC
            LIMIT 1;
            """
        else:  # Reporte general
            query = """
            SELECT c.nombre AS curso, c.codigo, e.nota, m.ciclo
            FROM evaluaciones e
            JOIN matriculas m ON e.matricula_id = m.id
            JOIN cursos c ON m.curso_id = c.id
            WHERE m.estudiante_id = %s
            ORDER BY m.ciclo DESC;
            """

        cursor.execute(query, (alumno_id,))
        notas = cursor.fetchall()

        if not notas:
            mensaje = "❗ Falta llevar los cursos o aún no tiene notas registradas."

    conn.close()
    return render_template("reporte_evaluaciones.html",
                           alumnos=alumnos,
                           notas=notas,
                           mensaje=mensaje,
                           alumno_seleccionado=alumno_seleccionado,
                           opcion=opcion)
