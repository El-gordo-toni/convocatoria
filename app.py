from flask import Flask, render_template, request, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import os
import re
from openpyxl import Workbook

app = Flask(__name__)
socketio = SocketIO(app)

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
# HOME
# =========================
@app.route("/", methods=["GET","POST"])
def index():

    error = None
    config = Config.query.first()
    menu_opciones = config.opciones_menu.split(",")

    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        apellido = request.form["apellido"].strip()
        matricula = request.form.get("matricula","").strip()
        asistencia = request.form.get("asistencia")

        if config.menu_activo and not asistencia:
            error = "Seleccioná una opción del menú"
        elif not solo_letras(nombre):
            error = "Nombre inválido"
        elif not solo_letras(apellido):
            error = "Apellido inválido"
        elif matricula and not solo_numeros(matricula):
            error = "Matrícula inválida"
        else:
            nuevo = Participante(
                nombre=nombre,
                apellido=apellido,
                matricula=matricula,
                asistencia=asistencia if asistencia else ""
            )
            db.session.add(nuevo)
            db.session.commit()

            # 🔥 EMITE A TODOS LOS CLIENTES
            socketio.emit("nuevo", {
                "nombre": nuevo.nombre,
                "apellido": nuevo.apellido
            })

            return redirect("/")

    participantes = Participante.query.order_by(Participante.id.desc()).all()
    bg = "/static_bg" if os.path.exists("/var/data/uploads/fondo.jpg") else None

    return render_template("index.html",
        participantes=participantes,
        menu_opciones=menu_opciones,
        menu_activo=config.menu_activo,
        error=error,
        admin=session.get("admin",False),
        bg_path=bg,
        config=config
    )

# =========================
# RESTO IGUAL (delete, reset, export, bg...)
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

@app.route("/export")
def export():
    if not session.get("admin"):
        return "No autorizado",403

    wb = Workbook()
    ws = wb.active
    ws.append(["Nombre","Apellido","Matrícula","Horario"])

    for p in Participante.query.all():
        ws.append([p.nombre,p.apellido,p.matricula,p.asistencia])

    path="/var/data/participantes.xlsx"
    wb.save(path)

    return send_file(path, as_attachment=True)

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

# 🔥 IMPORTANTE
if __name__ == "__main__":
    socketio.run(app, debug=True)
