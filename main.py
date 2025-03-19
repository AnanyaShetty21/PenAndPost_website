import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask_mysqldb import MySQL

load_dotenv()

app = Flask(__name__)
mysql = MySQL(app)

DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOSTNAME = os.getenv("DB_HOSTNAME")
DB_NAME = os.getenv("DB_NAME")
secret_key = os.getenv("secret_key")



app.config['MYSQL_USER'] = DB_USERNAME
app.config['MYSQL_PASSWORD'] = DB_PASSWORD
app.config['MYSQL_HOST'] = DB_HOSTNAME
app.config['MYSQL_DB'] = DB_NAME
app.config["SECRET_KEY"] = secret_key
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'


login_manager = LoginManager()
login_manager.init_app(app)


class Users(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password
        # self.dp = dp
        # self.followers = followers
        # self.following = following


def get_user_by_id(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM userinfo WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    if user_data:
        return Users(id=user_data['id'], username=user_data['username'], password=user_data['password'])
    return None

def get_blogs():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT blog.blogtitle, blog.content, blog.blogimg, blog.date, blog.likes, blog.category, userinfo.username, userinfo.dp 
        FROM blog 
        JOIN userinfo ON blog.userid = userinfo.id 
        ORDER BY blog.date DESC
        """)
    blogs = cursor.fetchall()
    cursor.close()
    return blogs


def get_users():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM userinfo")
    users = cursor.fetchall()
    cursor.close()
    return users


@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        password_hash = generate_password_hash(request.form.get("password"))
        username = request.form.get("username")

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO userinfo (username, password) VALUES (%s, %s)", (username, password_hash))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
	if request.method == "POST":
		username = request.form.get("username")
		password = request.form.get("password")
		cursor = mysql.connection.cursor()
		cursor.execute("SELECT * FROM userinfo WHERE username = %s", (username,))
		user_data = cursor.fetchone()
		cursor.close()
		
		if user_data and check_password_hash(user_data['password'], password):
			user = Users(id=user_data['id'], username=user_data['username'], password=user_data['password'])
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
    if request.method == "POST":
        blogtitle = request.form.get('blogtitle')
        content = request.form.get('content')
        draft = request.form.get('content')
        blogimg = request.files.get('blogimg') 
        if blogimg and blogimg.filename:
            filepath = os.path.join('static/images', blogimg_file.filename)
            blogimg_file.save(filepath) 
            blogimg = blogimg_file.filename 
        else:
            blogimg = 'static\images\\blogimg_placeholder.png'  
        category = request.form.get('category')
        status = int(request.form.get('status'))
        visibility = int(request.form.get('visibility'))

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM blog WHERE userid = %s AND draft = %s", (session["_user_id"], draft))
        existing_blog = cursor.fetchone()
        print(existing_blog)
        if existing_blog:
            cursor.execute("""
                UPDATE blog 
                SET blogtitle = %s, content = %s, draft = %s, blogimg = %s, category = %s, 
                    status = %s, visibility = %s
                WHERE idblogs = %s
            """, (blogtitle, content if visibility else None, draft, blogimg, category, 
                  1 if status else 0, 1 if visibility else 0, existing_blog['idblogs']))
        else:
            cursor.execute("""
                INSERT INTO blog (blogtitle, content, draft, blogimg, date, userid, category, status, visibility) 
                VALUES (%s, %s, %s, %s, CURRENT_DATE(), %s, %s, %s, %s)
            """, (blogtitle, content if visibility else None, draft, blogimg, session["_user_id"], category, 
                  1 if status else 0, 1 if visibility else 0))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for("home"))

    return render_template("writeblog.html")


@app.route("/")
def home():
	blogs = get_blogs()
	return render_template("home.html", blogs=blogs)


if __name__ == "__main__":
    app.run()
