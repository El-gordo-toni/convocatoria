from flask import Flask, render_template, request, redirect, Response, session, send_file
from flask_sqlalchemy import SQLAlchemy
import os
import re
from openpyxl import Workbook

app = Flask(__name__)

# =========================
# CONFIG
# =========================
app.secret_key = "super_secret_key"
ADMIN_PASSWORD = "admin"

if not os.path.exists("/var/data"):
    os.makedirs("/var/data")

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
    matricula = db.Column(db.String(50), nullable=True)
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
    password = request.form.get("password")

    if password == ADMIN_PASSWORD:
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

        # VALIDACIONES
        if not solo_letras(nombre):
            error = "El nombre solo puede contener letras"
        elif not solo_letras(apellido):
            error = "El apellido solo puede contener letras"
        elif matricula and not solo_numeros(matricula):
            error = "La matrícula solo puede contener números"
        else:
            # EVITAR DUPLICADOS
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

    return render_template(
        "index.html",
        van=van,
        no_van=no_van,
        error=error,
        admin=session.get("admin", False)
    )

# =========================
# BORRAR (ADMIN)
# =========================
@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("admin"):
        return "No autorizado", 403

    participante = Participante.query.get(id)
    if participante:
        db.session.delete(participante)
        db.session.commit()

    return redirect("/")

# =========================
# RESET (ADMIN)
# =========================
@app.route("/reset")
def reset():
    if not session.get("admin"):
        return "No autorizado", 403

    Participante.query.delete()
    db.session.commit()
    return redirect("/")

# =========================
# EXPORTAR EXCEL
# =========================
@app.route("/export")
def export():
    if not session.get("admin"):
        return "No autorizado", 403

    participantes = Participante.query.all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Participantes"

    ws.append(["Nombre", "Apellido", "Matrícula", "Asistencia"])

    for p in participantes:
        ws.append([p.nombre, p.apellido, p.matricula, p.asistencia])

    file_path = "/var/data/participantes.xlsx"
    wb.save(file_path)

    return send_file(file_path, as_attachment=True)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
