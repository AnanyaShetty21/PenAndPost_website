import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
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

class Blog(db.Model):
	__tablename__ = "blog"
	idblogs = db.Column(db.Integer, primary_key=True, autoincrement=True)
	blogtitle = db.Column(db.String(255), nullable=False)
	content = db.Column(db.Text, nullable=True)
	draft = db.Column(db.Text, nullable=True)
	blogimg = db.Column(db.String(500), nullable=True)
	date = db.Column(db.Date, nullable=False)
	userid = db.Column(db.Integer, db.ForeignKey('userinfo.id'), nullable=False)
	category = db.Column(db.String(45), nullable=True)
	visibility = db.Column(db.Integer, default=0)
	status = db.Column(db.Integer, default=0)
	likes = db.Column(db.Integer, default=0)


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


@app.route("/writeblog", methods=["POST", "GET"])
@login_required
def writeblog():
	if request.method=="POST":
		blogtitle = request.form.get('blogtitle')
		content = request.form.get('content')
		draft = request.form.get('content')
		blogimg = request.form.get('blogimg')
		category = request.form.get('category')
		status = int(request.form.get('status'))
		visibility = int(request.form.get('visibility'))
	
		existing_blog = Blog.query.filter_by(userid=session["_user_id"], draft=draft).first()

		if existing_blog:
			existing_blog.blogtitle = blogtitle
			existing_blog.content = content if visibility else None
			existing_blog.draft = draft 
			existing_blog.blogimg = blogimg
			existing_blog.category = category
			existing_blog.status = 1 if status else 0
			existing_blog.visibility = 1 if visibility else 0
		
		else:
			new_blog = Blog(
				blogtitle=blogtitle,
				content=content if visibility else None,
				draft=draft,
				blogimg=blogimg,
				date=db.func.current_date(),
				userid=session["_user_id"],
				category=category,
				status=1 if status else 0,
				visibility=1 if visibility else 0
				)
			db.session.add(new_blog)
		db.session.commit()
		return redirect(url_for("home"))
			

	return render_template("writeblog.html")
 


@app.route("/")
def home():
	return render_template("home.html")


if __name__ == "__main__":
    app.run()
