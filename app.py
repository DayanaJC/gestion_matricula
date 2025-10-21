# app.py
from flask import Flask, jsonify, render_template, request, redirect, url_for
from estudiantes import estudiantes_bp
from cursos import cursos_bp
from matriculas import matriculas_bp
from academico import academico_bp
from evaluaciones import evaluaciones_bp
from logger import log_event
import requests, time

app = Flask(__name__)

# Registrar Blueprints de servicios
app.register_blueprint(estudiantes_bp, url_prefix="/api/v1/continental.edu.pe/soa/estudiantes-service")
app.register_blueprint(cursos_bp, url_prefix="/api/v1/continental.edu.pe/soa/cursos-service")
app.register_blueprint(matriculas_bp, url_prefix="/api/v1/continental.edu.pe/soa/matriculas-service")
app.register_blueprint(academico_bp, url_prefix="/api/v1/continental.edu.pe/soa/academico-service")
app.register_blueprint(evaluaciones_bp, url_prefix="/api/v1/continental.edu.pe/soa/evaluaciones-service")

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
# Logging y errores
# -------------------------
@app.errorhandler(Exception)
def _on_error(e):
    log_event("app-core", "ERROR", "SERVICE", f"Unhandled: {type(e).__name__}: {e}")
    return jsonify({"status": "error", "message": "Error interno del servidor"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
