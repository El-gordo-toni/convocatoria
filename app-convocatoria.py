from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///datos.db")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Participante(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    apellido = db.Column(db.String(100))
    matricula = db.Column(db.String(50), nullable=True)
    asistencia = db.Column(db.String(10))  # "Si" o "No"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        matricula = request.form.get("matricula")  # puede venir vacío
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
    return render_template("index.html", participantes=participantes)

if __name__ == "__main__":
    app.run(debug=True)
