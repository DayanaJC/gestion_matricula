# app.py
from flask import Flask, jsonify, render_template, request, redirect, url_for
from estudiantes import estudiantes_bp
from cursos import cursos_bp
from matriculas import matriculas_bp
from academico import academico_bp
from evaluaciones import evaluaciones_bp
from reportes import reportes_bp
from logger import log_event
import requests, time






app = Flask(__name__)

# Registrar Blueprints de servicios
app.register_blueprint(estudiantes_bp, url_prefix="/api/v1/continental.edu.pe/soa/estudiantes-service")
app.register_blueprint(cursos_bp, url_prefix="/api/v1/continental.edu.pe/soa/cursos-service")
app.register_blueprint(matriculas_bp, url_prefix="/api/v1/continental.edu.pe/soa/matriculas-service")
app.register_blueprint(academico_bp, url_prefix="/api/v1/continental.edu.pe/soa/academico-service")
app.register_blueprint(evaluaciones_bp, url_prefix="/api/v1/continental.edu.pe/soa/evaluaciones-service")
app.register_blueprint(reportes_bp)
# Rutas de la interfaz web ----------------------------
BASE_URL = "http://127.0.0.1:5000/api/v1/continental.edu.pe/soa"

@app.route("/")
def home():
    return render_template("index.html")

# -------------------------
# INTERFAZ WEB: Alumnos
# -------------------------
@app.route("/alumnos")
def alumnos_list():
    resp = requests.get(f"{BASE_URL}/estudiantes-service/")
    alumnos = resp.json().get("data", []) if resp.status_code == 200 else []
    return render_template("alumnos.html", alumnos=alumnos)

@app.route("/alumnos/nuevo", methods=["GET", "POST"])
def alumnos_nuevo():
    if request.method == "POST":
        data = {
            "codigo": request.form["codigo"],
            "nombre": request.form["nombre"],
            "correo": request.form["correo"],
            "carrera": request.form["carrera"],
            "ciclo": request.form["ciclo"],
            "estado": request.form.get("estado", "activo")
        }
        requests.post(f"{BASE_URL}/estudiantes-service/", json=data)
        return redirect(url_for("alumnos_list"))
    return render_template("alumno_form.html")

@app.route("/alumnos/eliminar/<int:id>")
def alumnos_eliminar(id):
    requests.delete(f"{BASE_URL}/estudiantes-service/{id}")
    return redirect(url_for("alumnos_list"))

# -------------------------
# INTERFAZ WEB: Cursos
# -------------------------
@app.route("/cursos")
def cursos_list():
    resp = requests.get(f"{BASE_URL}/cursos-service/")
    cursos = resp.json().get("data", []) if resp.status_code == 200 else []
    return render_template("cursos.html", cursos=cursos)

@app.route("/cursos/nuevo", methods=["GET", "POST"])
def cursos_nuevo():
    if request.method == "POST":
        data = {
            "codigo": request.form["codigo"],
            "nombre": request.form["nombre"],
            "creditos": request.form["creditos"],
            "ciclo": request.form["ciclo"]
        }
        requests.post(f"{BASE_URL}/cursos-service/", json=data)
        return redirect(url_for("cursos_list"))
    return render_template("curso_form.html")

@app.route("/cursos/eliminar/<int:id>")
def cursos_eliminar(id):
    requests.delete(f"{BASE_URL}/cursos-service/{id}")
    return redirect(url_for("cursos_list"))

# -------------------------
# INTERFAZ WEB: Matrículas
# -------------------------
@app.route("/matriculas")
def matriculas_list():
    """Mostrar la tabla de matrículas"""
    resp = requests.get(f"{BASE_URL}/matriculas-service/listar")
    matriculas = resp.json() if resp.status_code == 200 else []
    return render_template("matriculas.html", matriculas=matriculas)

@app.route("/matriculas/nuevo", methods=["GET", "POST"])
def matriculas_nuevo():
    """Formulario para registrar matrículas"""
    # Obtener estudiantes y cursos desde las APIs
    resp_est = requests.get(f"{BASE_URL}/estudiantes-service/")
    resp_cur = requests.get(f"{BASE_URL}/cursos-service/")
    estudiantes = resp_est.json().get("data", []) if resp_est.status_code == 200 else []
    cursos = resp_cur.json().get("data", []) if resp_cur.status_code == 200 else []

    if request.method == "POST":
        data = {
            "estudiante_id": request.form["estudiante_id"],
            "curso_id": request.form["curso_id"]
        }
        requests.post(f"{BASE_URL}/matriculas-service/", json=data)
        return redirect(url_for("matriculas_list"))

    return render_template("matricula_form.html", estudiantes=estudiantes, cursos=cursos)

# -------------------------
# INTERFAZ WEB: Evaluaciones
# -------------------------
@app.route("/evaluaciones")
def evaluaciones_list():
    # Llamamos directamente al blueprint que lista evaluaciones para la web
    # La idea es obtener un listado simple de registros
    try:
        resp = requests.get(f"{BASE_URL}/evaluaciones-service/")
        evaluaciones = resp.json().get("data", []) if resp.status_code == 200 else []
    except Exception as e:
        evaluaciones = []
    return render_template("evaluaciones.html", evaluaciones=evaluaciones)

@app.route("/evaluaciones/nueva", methods=["GET", "POST"])
def evaluaciones_nueva():
    # Obtener estudiantes y cursos (igual que en matriculas/cursos)
    resp_est = requests.get(f"{BASE_URL}/estudiantes-service/")
    resp_cur = requests.get(f"{BASE_URL}/cursos-service/")
    estudiantes = resp_est.json().get("data", []) if resp_est.status_code == 200 else []
    cursos = resp_cur.json().get("data", []) if resp_cur.status_code == 200 else []

    if request.method == "POST":
        # En el form enviaremos codigo_estudiante y codigo_curso (igual que tu API espera)
        data = {
            "codigo_estudiante": request.form["codigo_estudiante"],
            "codigo_curso": request.form["codigo_curso"],
            "nota": request.form["nota"]
        }
        # Llamada al servicio API interno
        requests.post(f"{BASE_URL}/evaluaciones-service/", json=data)
        return redirect(url_for("evaluaciones_list"))

    return render_template("evaluacion_form.html", estudiantes=estudiantes, cursos=cursos)

# -------------------------
# INTERFAZ WEB: reporte_evaluaciones
# -------------------------

# -------------------------
# Logging y errores
# -------------------------
@app.errorhandler(Exception)
def _on_error(e):
    log_event("app-core", "ERROR", "SERVICE", f"Unhandled: {type(e).__name__}: {e}")
    return jsonify({"status": "error", "message": "Error interno del servidor"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
