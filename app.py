import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, session, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import os
import re
from openpyxl import Workbook

app = Flask(__name__)
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

app.secret_key = "super_secret_key"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

BASE_PATH = "/var/data"
UPLOAD_FOLDER = "/var/data/uploads"

os.makedirs(BASE_PATH, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////var/data/datos.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================
# MODELOS
# =========================
class Participante(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    matricula = db.Column(db.String(50))
    asistencia = db.Column(db.String(100), nullable=False)

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), default="🏌️ Torneo Matungo")
    subtitulo = db.Column(db.String(200), default="Anotate para la próxima fecha")
    subtitulo2 = db.Column(db.String(200), default="")
    subtitulo3 = db.Column(db.String(200), default="")
    opciones_menu = db.Column(db.Text, default="8:00 AM,9:00 AM,10:00 AM")
    menu_activo = db.Column(db.Boolean, default=True)

with app.app_context():
    db.create_all()
    if not Config.query.first():
        db.session.add(Config())
        db.session.commit()

# =========================
# VALIDACIONES
# =========================
def solo_letras(t): return re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$", t)
def solo_numeros(t): return re.match(r"^[0-9]+$", t)

# =========================
# ADMIN
# =========================
@app.route("/admin", methods=["POST"])
def admin_login():
    if request.form.get("password") == ADMIN_PASSWORD:
        session["admin"] = True
    return redirect("/")

@app.route("/admin-secret")
def admin_secret():
    return render_template("admin_login.html")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

# =========================
# API REGISTRO (SIN RECARGA)
# =========================
@app.route("/registrar", methods=["POST"])
def registrar():

    config = Config.query.first()

    nombre = request.form["nombre"].strip()
    apellido = request.form["apellido"].strip()
    matricula = request.form.get("matricula","").strip()
    asistencia = request.form.get("asistencia")

    if config.menu_activo and not asistencia:
        return jsonify({"ok":False,"msg":"Seleccioná una opción"})
    if not solo_letras(nombre):
        return jsonify({"ok":False,"msg":"Nombre inválido"})
    if not solo_letras(apellido):
        return jsonify({"ok":False,"msg":"Apellido inválido"})
    if matricula and not solo_numeros(matricula):
        return jsonify({"ok":False,"msg":"Matrícula inválida"})

    nuevo = Participante(
        nombre=nombre,
        apellido=apellido,
        matricula=matricula,
        asistencia=asistencia if asistencia else ""
    )
    db.session.add(nuevo)
    db.session.commit()

    socketio.emit("nuevo", {
        "nombre": nuevo.nombre,
        "apellido": nuevo.apellido
    }, broadcast=True)

    return jsonify({"ok":True})
    
# =========================
# HOME
# =========================
@app.route("/")
def index():

    config = Config.query.first()
    participantes = Participante.query.order_by(Participante.id.desc()).all()
    menu_opciones = config.opciones_menu.split(",")

    bg = "/static_bg" if os.path.exists("/var/data/uploads/fondo.jpg") else None

    return render_template("index.html",
        participantes=participantes,
        menu_opciones=menu_opciones,
        menu_activo=config.menu_activo,
        admin=session.get("admin",False),
        bg_path=bg,
        config=config
    )

# =========================
# RUN
# =========================
if __name__ == "__main__":
    socketio.run(app, debug=True)
