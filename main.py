import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
pymysql.install_as_MySQLdb()
from dotenv import load_dotenv
from urllib.parse import quote


load_dotenv()



app = Flask(__name__)


DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = quote(os.getenv("DB_PASSWORD"))
DB_HOSTNAME = os.getenv("DB_HOSTNAME")
DB_NAME = os.getenv("DB_NAME")
secret_key = os.getenv("secret_key")

app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOSTNAME}/{DB_NAME}"
app.config["SECRET_KEY"] = secret_key
db = SQLAlchemy()


login_manager = LoginManager()
login_manager.init_app(app)



class Users(UserMixin, db.Model):
	__tablename__ = "userinfo"
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(250), unique=True,
						nullable=False)
	password = db.Column(db.String(250),
						nullable=False)



db.init_app(app)


with app.app_context():
	db.create_all()


@login_manager.user_loader
def loader_user(user_id):
	return Users.query.get(user_id)


@app.route('/register', methods=["GET", "POST"])
def register():
	if request.method == "POST":
		password_hash = generate_password_hash(request.form.get("password"))
		user = Users(username=request.form.get("username"),
					password=password_hash)
		db.session.add(user)
		db.session.commit()
		return redirect(url_for("login"))
	return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
	if request.method == "POST":
		user = Users.query.filter_by(username=request.form.get("username")).first()
		if user and check_password_hash(user.password, request.form.get("password")):
			login_user(user)
			return redirect(url_for("home"))
	return render_template("login.html")


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))
 


@app.route("/")
def home():
	return render_template("home.html")


if __name__ == "__main__":
    app.run()
