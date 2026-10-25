"""
TD2 - Exploitation de Flask-Admin
Etudiant : Amri Iheb
Module   : Développement web avec Python (INGTA2-S1)

Lancer :  python app.py   puis ouvrir  http://127.0.0.1:5000/admin
"""
import os
from datetime import date

from flask import Flask, redirect
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_babel import Babel
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.security import generate_password_hash
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Email, Length

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = "td2-flask-admin-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "database.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["FLASK_ADMIN_SWATCH"] = "flatly"  # thème Bootswatch
app.config["BABEL_DEFAULT_LOCALE"] = "fr"

db = SQLAlchemy(app)
babel = Babel(app, locale_selector=lambda: "fr")


# Active les clés étrangères (CASCADE) dans SQLite
@event.listens_for(Engine, "connect")
def _enable_sqlite_fk(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ----------------------------------------------------------------------------
# Modèles
# ----------------------------------------------------------------------------
class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(200), unique=True)
    password = db.Column(db.String(200))

    def __str__(self):
        return self.username


class Classe(db.Model):
    __tablename__ = "classe"
    cod_class = db.Column(db.String(20), primary_key=True)
    nom_class = db.Column(db.String(100), nullable=False)
    nbr_etud = db.Column(db.Integer)

    # Relation : une classe a plusieurs étudiants
    etudiants = db.relationship("Etudiant", back_populates="classe_r", passive_deletes=True)

    def __str__(self):
        return self.nom_class


class Etudiant(db.Model):
    __tablename__ = "etudiant"
    nce = db.Column(db.String(20), primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    date_nais = db.Column(db.Date)
    lieu_nais = db.Column(db.String(100))

    # Clé étrangère vers Classe
    cod_class = db.Column(
        db.String(20),
        db.ForeignKey("classe.cod_class", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    classe_r = db.relationship("Classe", back_populates="etudiants")

    # Relation vers les absences
    absences = db.relationship("Absence", back_populates="etudiant_r", passive_deletes=True)

    def __str__(self):
        return f"{self.nom} {self.prenom}"


class Matiere(db.Model):
    __tablename__ = "matiere"
    cod_mat = db.Column(db.String(20), primary_key=True)
    int_mat = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

    # Relation vers les absences
    absences = db.relationship("Absence", back_populates="matiere_r", passive_deletes=True)

    def __str__(self):
        return self.int_mat


class Absence(db.Model):
    __tablename__ = "absence"
    id = db.Column(db.Integer, primary_key=True)
    date_a = db.Column(db.Date, nullable=False)
    nha = db.Column(db.Integer, default=0)

    # Clés étrangères
    cod_mat = db.Column(
        db.String(20),
        db.ForeignKey("matiere.cod_mat", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    nce = db.Column(
        db.String(20),
        db.ForeignKey("etudiant.nce", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )

    # Liaisons
    matiere_r = db.relationship("Matiere", back_populates="absences")
    etudiant_r = db.relationship("Etudiant", back_populates="absences")

    def __str__(self):
        return f"Absence {self.id}"


# ----------------------------------------------------------------------------
# Formulaire + vues Flask-Admin
# ----------------------------------------------------------------------------
class UserForm(FlaskForm):
    class Meta:
        csrf = False  # Flask-Admin gère son propre formulaire

    username = StringField("Nom d'utilisateur", validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Mot de passe", validators=[DataRequired(), Length(min=6)])


class BaseView(ModelView):
    page_size = 10
    can_set_page_size = True
    can_view_details = True
    can_export = True
    export_types = ["csv"]
    create_modal = True
    edit_modal = True
    details_modal = True


class UserAdmin(BaseView):
    form = UserForm
    page_size = 5
    column_exclude_list = ["password"]  # cache le mot de passe dans la liste
    column_labels = {"username": "Utilisateur", "email": "Email"}
    column_searchable_list = ("username", "email")
    column_details_exclude_list = ["password"]

    def on_model_change(self, form, model, is_created):
        # Chiffre le mot de passe à la création / modification
        if form.password.data:
            model.password = generate_password_hash(form.password.data)


class ClasseAdmin(BaseView):
    column_list = ("cod_class", "nom_class", "nbr_etud")
    column_labels = {"cod_class": "Code", "nom_class": "Classe", "nbr_etud": "Nb étudiants"}
    column_searchable_list = ("cod_class", "nom_class")


class EtudiantAdmin(BaseView):
    column_list = ("nce", "nom", "prenom", "date_nais", "lieu_nais", "classe_r")
    column_labels = {"nce": "N° carte", "nom": "Nom", "prenom": "Prénom",
                     "date_nais": "Date de naissance", "lieu_nais": "Lieu de naissance",
                     "classe_r": "Classe"}
    column_searchable_list = ("nce", "nom", "prenom")
    column_filters = ("cod_class", "lieu_nais")
    form_columns = ("nce", "nom", "prenom", "date_nais", "lieu_nais", "classe_r")


class MatiereAdmin(BaseView):
    column_list = ("cod_mat", "int_mat", "description")
    column_labels = {"cod_mat": "Code", "int_mat": "Intitulé", "description": "Description"}
    column_searchable_list = ("cod_mat", "int_mat")


class AbsenceAdmin(BaseView):
    column_list = ("date_a", "etudiant_r", "matiere_r", "nha")
    column_labels = {"date_a": "Date", "etudiant_r": "Étudiant", "matiere_r": "Matière",
                     "nha": "Heures d'absence"}
    column_filters = ("date_a", "cod_mat", "nce")
    column_default_sort = ("date_a", True)
    form_columns = ("date_a", "nha", "matiere_r", "etudiant_r")


class DashboardView(AdminIndexView):
    @expose("/")
    def index(self):
        stats = {
            "etudiants": Etudiant.query.count(),
            "classes": Classe.query.count(),
            "matieres": Matiere.query.count(),
            "heures": db.session.query(db.func.coalesce(db.func.sum(Absence.nha), 0)).scalar(),
        }
        dernieres = Absence.query.order_by(Absence.date_a.desc()).limit(5).all()
        return self.render("admin/index.html", stats=stats, dernieres=dernieres)


admin = Admin(app, name="Gestion Scolaire", template_mode="bootstrap3",
              index_view=DashboardView(name="Tableau de bord"))
admin.add_view(ClasseAdmin(Classe, db.session, name="Classes", category="Scolarité"))
admin.add_view(EtudiantAdmin(Etudiant, db.session, name="Étudiants", category="Scolarité"))
admin.add_view(MatiereAdmin(Matiere, db.session, name="Matières", category="Scolarité"))
admin.add_view(AbsenceAdmin(Absence, db.session, name="Absences", category="Scolarité"))
admin.add_view(UserAdmin(User, db.session, name="Utilisateurs", category="Administration"))


@app.route("/")
def index():
    return redirect("/admin/")


# ----------------------------------------------------------------------------
# Données de démonstration (créées une seule fois)
# ----------------------------------------------------------------------------
def seed():
    if User.query.first():
        return
    for name in ["admin", "admin1", "admin2", "admin3"]:
        db.session.add(User(username=name, email=f"{name}@gmail.com",
                            password=generate_password_hash("123456")))

    db.session.add_all([
        Classe(cod_class="INGTA2", nom_class="Ingénieur TA 2", nbr_etud=2),
        Classe(cod_class="INGTA1", nom_class="Ingénieur TA 1", nbr_etud=1),
    ])
    db.session.add_all([
        Etudiant(nce="E001", nom="Amri", prenom="Iheb", date_nais=date(2003, 5, 12),
                 lieu_nais="Tunis", cod_class="INGTA2"),
        Etudiant(nce="E002", nom="Ben Ali", prenom="Sara", date_nais=date(2003, 8, 3),
                 lieu_nais="Sfax", cod_class="INGTA2"),
        Etudiant(nce="E003", nom="Trabelsi", prenom="Omar", date_nais=date(2004, 1, 20),
                 lieu_nais="Sousse", cod_class="INGTA1"),
    ])
    db.session.add_all([
        Matiere(cod_mat="WEB", int_mat="Développement web avec Python",
                description="Flask, SQLAlchemy, Flask-Admin"),
        Matiere(cod_mat="BDD", int_mat="Bases de données", description="SQL et modélisation"),
    ])
    db.session.add_all([
        Absence(date_a=date(2026, 10, 5), nha=2, cod_mat="WEB", nce="E001"),
        Absence(date_a=date(2026, 10, 12), nha=3, cod_mat="BDD", nce="E002"),
    ])
    db.session.commit()


with app.app_context():
    db.create_all()
    seed()

if __name__ == "__main__":
    app.run(debug=True)
