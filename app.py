# app.py
from flask import Flask, jsonify
from estudiantes import estudiantes_bp
from cursos import cursos_bp
from matriculas import matriculas_bp
from academico import academico_bp
from evaluaciones import evaluaciones_bp  # si lo tienes
from logger import log_event

app = Flask(__name__)

# Registrar blueprints con dominio lógico /api/v1
app.register_blueprint(estudiantes_bp, url_prefix="/api/v1/continental.edu.pe/soa/estudiantes-service")
app.register_blueprint(cursos_bp, url_prefix="/api/v1/continental.edu.pe/soa/cursos-service")
app.register_blueprint(matriculas_bp, url_prefix="/api/v1/continental.edu.pe/soa/matriculas-service")
app.register_blueprint(academico_bp, url_prefix="/api/v1/continental.edu.pe/soa/academico-service")
app.register_blueprint(evaluaciones_bp, url_prefix="/api/v1/continental.edu.pe/soa/evaluaciones-service")  # si lo tienes

@app.route("/", methods=["GET"])
def root():
    return jsonify({"message": "API SOA Gestión de Matrícula - continental.edu.pe/soa"}), 200

@app.before_request
def _before():
    # aquí podrías iniciar trazas por request_id si quieres
    pass

@app.after_request
def _after(resp):
    # ejemplo: podrías loggear métricas globales aquí
    return resp

@app.errorhandler(Exception)
def _on_error(e):
    log_event("app-core", "ERROR", "SERVICE", f"Unhandled: {type(e).__name__}: {e}")
    return jsonify({"status":"error","message":"Error interno del servidor"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
