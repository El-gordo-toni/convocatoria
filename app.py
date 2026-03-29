from flask import Flask, render_template, request, redirect, Response, session, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import re
import json

app = Flask(__name__)

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
    nombre = db.Column(db.String(100))
    apellido = db.Column(db.String(100))
    matricula = db.Column(db.String(50))
    asistencia = db.Column(db.String(50))

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), default="🏌️ Torneo Matungo")
    subtitulo = db.Column(db.String(200), default="Anotate para la próxima fecha")
    opciones = db.Column(db.Text, default='["Confirmado","Duda","No juega"]')

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

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

# =========================
# HOME
# =========================
@app.route("/", methods=["GET","POST","HEAD"])
def index():
    if request.method == "HEAD":
        return Response(status=200)

    error = None
    config = Config.query.first()

    if request.method == "POST":
        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        matricula = request.form.get("matricula","")
        asistencia = request.form["asistencia"]

        if not solo_letras(nombre):
            error = "Nombre inválido"
        elif not solo_letras(apellido):
            error = "Apellido inválido"
        elif matricula and not solo_numeros(matricula):
            error = "Matrícula inválida"
        else:
            db.session.add(Participante(
                nombre=nombre,
                apellido=apellido,
                matricula=matricula,
                asistencia=asistencia
            ))
            db.session.commit()
            return redirect("/")

    participantes = Participante.query.order_by(Participante.id.desc()).all()

    bg = "/static_bg" if os.path.exists("/var/data/uploads/fondo.jpg") else None

    return render_template("index.html",
        participantes=participantes,
        admin=session.get("admin",False),
        config=config,
        opciones=json.loads(config.opciones),
        bg_path=bg
    )

# =========================
# DATA
# =========================
@app.route("/data")
def data():
    participantes = Participante.query.order_by(Participante.id.desc()).all()

    return jsonify({
        "jugadores":[
            {
                "id":p.id,
                "nombre":p.nombre,
                "apellido":p.apellido,
                "asistencia":p.asistencia
            } for p in participantes
        ]
    })

# =========================
# CONFIG
# =========================
@app.route("/update_config", methods=["POST"])
def update_config():
    if not session.get("admin"):
        return "No autorizado",403

    config = Config.query.first()

    config.titulo = request.form.get("titulo")
    config.subtitulo = request.form.get("subtitulo")

    opciones = request.form.get("opciones")
    config.opciones = json.dumps(opciones.split(","))

    db.session.commit()
    return redirect("/")

# =========================
# FONDO
# =========================
@app.route("/upload_bg", methods=["POST"])
def upload_bg():
    if not session.get("admin"):
        return "No autorizado",403

    file = request.files.get("imagen")

    if file:
        file.save("/var/data/uploads/fondo.jpg")

    return redirect("/")

@app.route("/static_bg")
def bg():
    return send_file("/var/data/uploads/fondo.jpg")

# =========================
# BORRAR / RESET
# =========================
@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("admin"):
        return "No autorizado",403

    p = Participante.query.get(id)
    if p:
        db.session.delete(p)
        db.session.commit()

    return redirect("/")

@app.route("/reset")
def reset():
    if not session.get("admin"):
        return "No autorizado",403

    Participante.query.delete()
    db.session.commit()
    return redirect("/")

# =========================
if __name__ == "__main__":
    app.run(debug=True)
