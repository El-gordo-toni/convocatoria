from flask import Flask, render_template, request, redirect, Response, session, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import re
from openpyxl import Workbook
from werkzeug.utils import secure_filename

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

class Participante(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    matricula = db.Column(db.String(50))
    asistencia = db.Column(db.String(10), nullable=False)

with app.app_context():
    db.create_all()

def solo_letras(t): return re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$", t)
def solo_numeros(t): return re.match(r"^[0-9]+$", t)

@app.route("/admin", methods=["POST"])
def admin_login():
    if request.form.get("password") == ADMIN_PASSWORD:
        session["admin"] = True
    return redirect("/")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

@app.route("/", methods=["GET","POST","HEAD"])
def index():
    if request.method == "HEAD":
        return Response(status=200)

    error = None

    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        apellido = request.form["apellido"].strip()
        matricula = request.form.get("matricula","").strip()
        asistencia = request.form["asistencia"]

        if not solo_letras(nombre):
            error = "Nombre inválido"
        elif not solo_letras(apellido):
            error = "Apellido inválido"
        elif matricula and not solo_numeros(matricula):
            error = "Matrícula inválida"
        else:
            if Participante.query.filter_by(nombre=nombre, apellido=apellido).first():
                error = "Ya anotado"
            else:
                db.session.add(Participante(
                    nombre=nombre,
                    apellido=apellido,
                    matricula=matricula,
                    asistencia=asistencia
                ))
                db.session.commit()
                return redirect("/")

    participantes = Participante.query.all()
    van = [p for p in participantes if p.asistencia=="Si"]
    no_van = [p for p in participantes if p.asistencia=="No"]

    bg = "/static_bg" if os.path.exists("/var/data/uploads/fondo.jpg") else None

    return render_template("index.html",
        van=van, no_van=no_van,
        error=error,
        admin=session.get("admin",False),
        bg_path=bg
    )

@app.route("/data")
def data():
    participantes = Participante.query.all()
    return jsonify({
        "van":[{"nombre":p.nombre,"apellido":p.apellido} for p in participantes if p.asistencia=="Si"],
        "no_van":[{"nombre":p.nombre,"apellido":p.apellido} for p in participantes if p.asistencia=="No"]
    })

@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("admin"): return "No autorizado",403
    p = Participante.query.get(id)
    if p:
        db.session.delete(p)
        db.session.commit()
    return redirect("/")

@app.route("/reset")
def reset():
    if not session.get("admin"): return "No autorizado",403
    Participante.query.delete()
    db.session.commit()
    return redirect("/")

@app.route("/export")
def export():
    if not session.get("admin"): return "No autorizado",403
    wb = Workbook()
    ws = wb.active
    ws.append(["Nombre","Apellido","Matrícula","Asistencia"])
    for p in Participante.query.all():
        ws.append([p.nombre,p.apellido,p.matricula,p.asistencia])
    path="/var/data/participantes.xlsx"
    wb.save(path)
    return send_file(path, as_attachment=True)

@app.route("/upload_bg", methods=["POST"])
def upload_bg():
    if not session.get("admin"): return "No autorizado",403
    file = request.files.get("imagen")
    if file and file.filename.lower().endswith(('.png','.jpg','.jpeg')):
        file.save("/var/data/uploads/fondo.jpg")
    return redirect("/")

@app.route("/static_bg")
def bg():
    return send_file("/var/data/uploads/fondo.jpg")

if __name__ == "__main__":
    app.run(debug=True)
