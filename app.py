from flask import Flask, render_template, request, redirect, Response, session, send_file
from flask_sqlalchemy import SQLAlchemy
import os
import re
from openpyxl import Workbook

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
@app.route("/", methods=["GET","POST","HEAD"])
def index():
    if request.method == "HEAD":
        return Response(status=200)

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
            if Participante.query.filter_by(nombre=nombre, apellido=apellido).first():
                error = "Ya anotado"
            else:
                db.session.add(Participante(
                    nombre=nombre,
                    apellido=apellido,
                    matricula=matricula,
                    asistencia=asistencia if asistencia else ""
                ))
                db.session.commit()
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
# CONFIG
# =========================
@app.route("/update_config", methods=["POST"])
def update_config():
    if not session.get("admin"):
        return "No autorizado",403

    config = Config.query.first()

    config.titulo = request.form.get("titulo")
    config.subtitulo = request.form.get("subtitulo")
    config.subtitulo2 = request.form.get("subtitulo2")
    config.subtitulo3 = request.form.get("subtitulo3")

    config.opciones_menu = request.form.get("opciones_menu")
    config.menu_activo = True if request.form.get("menu_activo") == "on" else False

    db.session.commit()
    return redirect("/")

# =========================
# BORRAR
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

# =========================
# RESET
# =========================
@app.route("/reset")
def reset():
    if not session.get("admin"):
        return "No autorizado",403

    Participante.query.delete()
    db.session.commit()
    return redirect("/")

# =========================
# EXPORT
# =========================
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

# =========================
# FONDO
# =========================
@app.route("/upload_bg", methods=["POST"])
def upload_bg():
    if not session.get("admin"):
        return "No autorizado",403

    file = request.files.get("imagen")

    if file and file.filename.lower().endswith(('.png','.jpg','.jpeg')):
        file.save("/var/data/uploads/fondo.jpg")

    return redirect("/")

@app.route("/static_bg")
def bg():
    return send_file("/var/data/uploads/fondo.jpg")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
