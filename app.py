from flask import Flask, render_template, request, redirect, Response
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Asegurar carpeta persistente (Render usa /var/data)
if not os.path.exists("/var/data"):
    os.makedirs("/var/data")

# Config DB
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////var/data/datos.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Modelo
class Participante(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    matricula = db.Column(db.String(50), nullable=True)
    asistencia = db.Column(db.String(10), nullable=False)  # "Si" o "No"

# Crear DB si no existe
with app.app_context():
    db.create_all()

# Ruta principal
@app.route("/", methods=["GET", "POST", "HEAD"])
def index():
    # Para evitar error de Render con HEAD
    if request.method == "HEAD":
        return Response(status=200)

    if request.method == "POST":
        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        matricula = request.form.get("matricula")
        asistencia = request.form["asistencia"]

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

    # Separar listas
    van = [p for p in participantes if p.asistencia == "Si"]
    no_van = [p for p in participantes if p.asistencia == "No"]

    return render_template("index.html", van=van, no_van=no_van)

# Reset lista (opcional)
@app.route("/reset")
def reset():
    Participante.query.delete()
    db.session.commit()
    return redirect("/")

# Run local
if __name__ == "__main__":
    app.run(debug=True)
