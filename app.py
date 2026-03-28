from flask import Flask, render_template, request, redirect, Response, session, send_file
from flask_sqlalchemy import SQLAlchemy
import os
import re
from openpyxl import Workbook
from werkzeug.utils import secure_filename

app = Flask(__name__)

# =========================
# CONFIG
# =========================
app.secret_key = "super_secret_key"
ADMIN_PASSWORD = "admin"

# Carpetas
BASE_PATH = "/var/data"
UPLOAD_FOLDER = "/var/data/uploads"

if not os.path.exists(BASE_PATH):
    os.makedirs(BASE_PATH)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# DB
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////var/data/datos.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================
# MODELO
# =========================
class Participante(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    matricula = db.Column(db.String(50))
    asistencia = db.Column(db.String(10), nullable=False)

with app.app_context():
    db.create_all()

# =========================
# VALIDACIONES
# =========================
def solo_letras(texto):
    return re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$", texto)

def solo_numeros(texto):
    return re.match(r"^[0-9]+$", texto)

# =========================
# LOGIN ADMIN
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
@app.route("/", methods=["GET", "POST", "HEAD"])
def index():
    if request.method == "HEAD":
        return Response(status=200)

    error = None

    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        apellido = request.form["apellido"].strip()
        matricula = request.form.get("matricula", "").strip()
        asistencia = request.form["asistencia"]

        if not solo_letras(nombre):
            error = "El nombre solo puede tener letras"
        elif not solo_letras(apellido):
            error = "El apellido solo puede tener letras"
        elif matricula and not solo_numeros(matricula):
            error = "La matrícula solo puede tener números"
        else:
            existe = Participante.query.filter_by(
                nombre=nombre,
                apellido=apellido
            ).first()

            if existe:
                error = "Este jugador ya está anotado"
            else:
                nuevo = Participante(
                    nombre=nombre,
                    apellido=apellido,
                    matricula=matricula,
                    asistencia=asistencia
                )
                db.session.add(nuevo)
                db.session.commit()
                return redirect("/")

    participantes = Participante.query.all()
    van = [p for p in participantes if p.asistencia == "Si"]
    no_van = [p for p in participantes if p.asistencia == "No"]

    # Fondo dinámico
    bg_file = "/var/data/uploads/fondo.jpg"
    bg_path = "/static_bg" if os.path.exists(bg_file) else None

    return render_template(
        "index.html",
        van=van,
        no_van=no_van,
        error=error,
        admin=session.get("admin", False),
        bg_path=bg_path
    )

# =========================
# BORRAR
# =========================
@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("admin"):
        return "No autorizado", 403

    p = Participante.query.get(id)
    if p:
        db.session.delete(p)
        db.session.commit()

    return redirect("/")

# =========================
# RESET
# =========================
@app.route("/reset")
def reset():
    if not session.get("admin"):
        return "No autorizado", 403

    Participante.query.delete()
    db.session.commit()
    return redirect("/")

# =========================
# EXPORT EXCEL
# =========================
@app.route("/export")
def export():
    if not session.get("admin"):
        return "No autorizado", 403

    wb = Workbook()
    ws = wb.active
    ws.append(["Nombre", "Apellido", "Matrícula", "Asistencia"])

    for p in Participante.query.all():
        ws.append([p.nombre, p.apellido, p.matricula, p.asistencia])

    file_path = "/var/data/participantes.xlsx"
    wb.save(file_path)

    return send_file(file_path, as_attachment=True)

# =========================
# SUBIR FONDO
# =========================
@app.route("/upload_bg", methods=["POST"])
def upload_bg():
    if not session.get("admin"):
        return "No autorizado", 403

    file = request.files.get("imagen")

    if file:
        filename = secure_filename("fondo.jpg")
        file.save(os.path.join(UPLOAD_FOLDER, filename))

    return redirect("/")

@app.route("/static_bg")
def static_bg():
    return send_file("/var/data/uploads/fondo.jpg")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
