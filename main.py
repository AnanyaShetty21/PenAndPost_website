import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask_mysqldb import MySQL

load_dotenv()

app = Flask(__name__, static_url_path='/static')
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

def get_user_by_username(username):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM userinfo WHERE username = %s", (username,))
    user_data = cursor.fetchone()
    cursor.close()
    return user_data

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

def get_user_blogs(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT * FROM blog 
        WHERE userid = %s
        ORDER BY date DESC
    """, (user_id,))
    blogs = cursor.fetchall()
    cursor.close()
    return blogs

def get_user_public_blogs(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT * FROM blog 
        WHERE userid = %s AND visibility = %s
        ORDER BY date DESC
    """, (user_id, 1))
    blogs = cursor.fetchall()
    cursor.close()
    return blogs

def is_following(follower_id, following_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM follow WHERE follower_id = %s AND following_id = %s", 
                  (follower_id, following_id))
    result = cursor.fetchone()
    cursor.close()
    if result:
        return True
    return False

def has_liked_blog(user_id, blog_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM likedblogs WHERE userid = %s AND blogid = %s", 
                  (user_id, blog_id))
    result = cursor.fetchone()
    cursor.close()
    if result:
        return True
    return False


def get_followers(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT userinfo.id, userinfo.username, userinfo.dp
        FROM follow
        JOIN userinfo ON follow.follower_id = userinfo.id
        WHERE follow.following_id = %s
    """, (user_id,))
    followers = cursor.fetchall()
    cursor.close()
    return followers

def get_following(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT userinfo.id, userinfo.username, userinfo.dp
        FROM follow
        JOIN userinfo ON follow.following_id = userinfo.id
        WHERE follow.follower_id = %s
    """, (user_id,))
    following = cursor.fetchall()
    cursor.close()
    return following


@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)


@app.route('/register', methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM userinfo WHERE username = %s", (username,))
        user_data = cursor.fetchone()
        if user_data:
            error = "Username already exists"
            return render_template("register.html", error=error)
        password_hash = generate_password_hash(request.form.get("password"))
        dp = request.files.get("dp")
        if dp and dp.filename:
            filepath = os.path.join('static\\user_uploaded_dp', dp.filename)
            dp.save(filepath) 
            dp = filepath
        else:
            dp = 'static\\images\\defaultavatar.png'

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO userinfo (username, password, dp) VALUES (%s, %s, %s)", (username, password_hash, dp))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
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
        elif user_data and not check_password_hash(user_data['password'], password):
            error = "Incorrect password"
        elif not user_data:
            error = "User not found"
    return render_template("login.html", error=error)


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
        blogimg = request.files.get('blogimg') 
        if blogimg and blogimg.filename:
            filepath = os.path.join('static\\user_uploaded_images', blogimg.filename)
            blogimg.save(filepath) 
            blogimg = filepath
        else:
            blogimg = 'static\\images\\blogimg_placeholder.png'  
        category = request.form.get('category')
        visibility = int(request.form.get('visibility'))

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM blog WHERE userid = %s AND blogtitle = %s", (session["_user_id"], blogtitle))
        existing_blog = cursor.fetchone()
        if existing_blog:
            cursor.execute("""
                UPDATE blog 
                SET blogtitle = %s, content = %s, blogimg = %s, category = %s, 
                    status = %s, visibility = %s
                WHERE idblogs = %s""", (blogtitle, content, blogimg, category, 
                  1 if visibility else 0, existing_blog['idblogs']))
        else:
            cursor.execute("""
                INSERT INTO blog (blogtitle, content, blogimg, date, userid, category, visibility) 
                VALUES (%s, %s, %s, CURRENT_DATE(), %s, %s, %s)""", (blogtitle, content, blogimg, session["_user_id"], category, 
                  1 if visibility else 0))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for("home"))

    return render_template("writeblog.html")






@app.route("/like/<int:blog_id>", methods=["POST"])
def like_blog(blog_id):
    user_id = session.get("_user_id")
    if not user_id:
        return jsonify({"success": False, "redirect": url_for("login")})
    
    if has_liked_blog(user_id, blog_id):
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM likedblogs WHERE userid = %s AND blogid = %s", 
                      (user_id, blog_id))
        cursor.execute("UPDATE blog SET likes = likes - 1 WHERE idblogs = %s", (blog_id,))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"success": True, "action": "unliked"})
    else:
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO likedblogs (userid, blogid) VALUES (%s, %s)", 
                      (user_id, blog_id))
        cursor.execute("UPDATE blog SET likes = likes + 1 WHERE idblogs = %s", (blog_id,))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"success": True, "action": "liked"})


@app.route("/follow/<int:user_id>", methods=["POST"])
@login_required
def follow_user(user_id):
    follower_id = session["_user_id"]
    
    if int(follower_id) == user_id:
        return jsonify({"success": False, "message": "You cannot follow yourself"})
    
    if is_following(follower_id, user_id):
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM follow WHERE follower_id = %s AND following_id = %s", 
                      (follower_id, user_id))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"success": True, "action": "unfollowed"})
    else:
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO follow (follower_id, following_id) VALUES (%s, %s)", 
                      (follower_id, user_id))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"success": True, "action": "followed"})


@app.route("/profile")
@app.route("/profile/<username>")
def profile(username=None):
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    if username:
        user_data = get_user_by_username(username)
        if not user_data:
            return redirect(url_for("home"))
        user_id = user_data['id']
        is_own_profile = (int(session["_user_id"]) == user_id)
        if not is_following(session["_user_id"], user_id): 
            blogs = get_user_public_blogs(user_id)
        elif is_own_profile or is_following(session["_user_id"], user_id):
            blogs = get_user_blogs(user_id)
    else:
        user_id = session["_user_id"]
        user_data = get_user_by_id(user_id)
        is_own_profile = True
        blogs = get_user_blogs(user_id)
    
    followers = get_followers(user_id)
    following = get_following(user_id)
    
    is_following_user = False
    if not is_own_profile and current_user.is_authenticated:
        is_following_user = is_following(session["_user_id"], user_id)
    
    return render_template("profile.html", 
                          user=user_data, 
                          blogs=blogs, 
                          followers=followers, 
                          following=following,
                          is_own_profile=is_own_profile,
                          is_following=is_following_user)



@app.route("/edit/<int:blog_id>", methods=["GET", "POST"])
@login_required
def edit_blog(blog_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM blog WHERE idblogs = %s", (blog_id,))
    blog = cursor.fetchone()
    cursor.close()
    
    if not blog or str(blog['userid']) != session["_user_id"]:
        return redirect(url_for("home"))
    
    if request.method == "POST":
        blogtitle = request.form.get('blogtitle')
        content = request.form.get('content')
        blogimg = request.files.get('blogimg')
        
        if blogimg and blogimg.filename:
            filepath = os.path.join('static\\user_uploaded_images', blogimg.filename)
            blogimg.save(filepath)
            blogimg_path = filepath
        else:
            blogimg_path = blog['blogimg'] 
            
        category = request.form.get('category')
        visibility = int(request.form.get('visibility'))

        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE blog 
            SET blogtitle = %s, content = %s, blogimg = %s, category = %s, visibility = %s
            WHERE idblogs = %s""", (blogtitle, content, blogimg_path, category, 1 if visibility else 0, blog_id))
        
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for("view_blog", idblogs=blog_id))
    
    return render_template("writeblog.html", blog=blog, edit_mode=True)


@app.route("/delete/<int:blog_id>", methods=["POST"])
@login_required
def delete_blog(blog_id):
    cursor = mysql.connection.cursor()
    
    cursor.execute("SELECT * FROM blog WHERE idblogs = %s", (blog_id,))
    blog = cursor.fetchone()
    
    if not blog or str(blog['userid']) != session["_user_id"]:
        cursor.close()
        return redirect(url_for("home"))
        
    cursor.execute("DELETE FROM blog WHERE idblogs = %s", (blog_id,))
    mysql.connection.commit()
    cursor.close()
    
    return redirect(url_for("home"))


@app.route("/<int:idblogs>")
def view_blog(idblogs):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT blog.*, userinfo.username, userinfo.dp
        FROM blog 
        JOIN userinfo ON blog.userid = userinfo.id
        WHERE blog.idblogs = %s
    """, (idblogs,))
    blog = cursor.fetchone()
    cursor.close()
    
    if not blog:
        return redirect(url_for("home"))
    
    is_author = current_user.is_authenticated and str(blog['userid']) == session["_user_id"]
    is_following_author = current_user.is_authenticated and is_following(session["_user_id"], blog['userid'])
    
    if blog['visibility'] == 0 and not is_author and not is_following_author:
        return redirect(url_for("home"))
    
    has_liked = False
    if current_user.is_authenticated:
        has_liked = has_liked_blog(session["_user_id"], idblogs)
    
    return render_template("view_blog.html", blog=blog, has_liked=has_liked, is_author=is_author)


@app.route("/delete_profile", methods=["POST"])
@login_required
def delete_profile():
    user_id = session["_user_id"]
    
    try:
        cursor = mysql.connection.cursor()
        
        cursor.execute("DELETE FROM userinfo WHERE id = %s", (user_id,))
        
        mysql.connection.commit()
        cursor.close()
        
        logout_user()
        flash("Your profile has been successfully deleted", "success")
        return redirect(url_for("login"))
        
    except Exception as e:
        mysql.connection.rollback()
        flash("An error occurred while deleting your profile", "error")
        return redirect(url_for("profile"))



@app.route("/", methods=["GET"])
def home():
    selected_categories = request.args.getlist("category")
    yourblogs = request.args.get("yourblogs")
    sort_by_popular = request.args.get("popular")
    
    params = []
    cursor = mysql.connection.cursor()
    
    query = """
        SELECT blog.idblogs, blog.blogtitle, blog.content, blog.blogimg, blog.date, 
               blog.likes, blog.category, blog.userid, userinfo.username, userinfo.dp 
        FROM blog 
        JOIN userinfo ON blog.userid = userinfo.id
        WHERE (blog.visibility = 1
    """
   
    if current_user.is_authenticated:
        query += """ OR (blog.visibility = 0 AND blog.userid IN 
                    (SELECT following_id FROM follow WHERE follower_id = %s))
                    OR blog.userid = %s"""
        params.append(session["_user_id"])
        params.append(session["_user_id"])
    
    query += ")"
    
    if yourblogs:
        query += " AND blog.userid = %s"
        params.append(session["_user_id"])
        
    if selected_categories:
        query += " AND blog.category IN ("
        for i in range(len(selected_categories)-1):
            query += "%s, "
        query += "%s)"
        params.extend(selected_categories)
    
    if sort_by_popular:
        query += " ORDER BY blog.likes DESC"
    else:
        query += " ORDER BY blog.date DESC"
    
    cursor.execute(query, params)
    blogs = cursor.fetchall()
    cursor.close()

    return render_template("home.html", blogs=blogs)



if __name__ == "__main__":
    app.run()
