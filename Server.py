import os
import time
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import timedelta, datetime
import json
from markupsafe import escape

with open("config/flask_config.json") as config_file:
    config = json.load(config_file)

port = config.get("port", 5000)
host = config.get("host", "0.0.0.0")

blue = "\033[34m"
yellow = "\033[33m"
white = "\033[37m"
reset = "\033[0m"
red = "\033[31m"

print(f"""{blue}
 SSSSS  EEEEE  RRRR   V   V  EEEEE  RRRR  
S       E      R   R  V   V  E      R   R 
 SSS    EEEE   RRRR   V   V  EEEE   RRRR  
    S   E      R  R   V   V  E      R  R  
SSSS    EEEEE  R   R   VVV   EEEEE  R   R 
{reset}""")
time.sleep(1)
print(f"{red}Attempting to start Flask server on IP -> {host}:{port}{reset}")
print(f"{red}Please wait...{reset}")
time.sleep(1)
secret_key_pre = os.urandom(25)
print(f"{yellow}Your Secret Key for this Web Session is: {secret_key_pre}{reset}")
time.sleep(3)

app = Flask(__name__)
app.secret_key = secret_key_pre
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

def get_db_connection():
    conn = sqlite3.connect("t4xnetwork_data.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                postid INTEGER PRIMARY KEY AUTOINCREMENT,
                userid INTEGER NOT NULL,
                posttext TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (userid) REFERENCES users (id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                postid INTEGER NOT NULL,
                userid INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (postid) REFERENCES posts (postid) ON DELETE CASCADE,
                FOREIGN KEY (userid) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(postid, userid)
            )
        """)
    conn.close()


init_db()

def sanitize_input(user_input):
    return escape(user_input)


def render_homepage():
    username = session.get('username')
    conn = get_db_connection()
    
    current_user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    
    posts = conn.execute("""
        SELECT p.postid, p.posttext, p.created_at, u.username,
               COUNT(l.id) as like_count
        FROM posts p 
        JOIN users u ON p.userid = u.id 
        LEFT JOIN likes l ON p.postid = l.postid
        GROUP BY p.postid, p.posttext, p.created_at, u.username
        ORDER BY p.created_at DESC
        LIMIT 5
    """).fetchall()
    
    posts_with_like_status = []
    for post in posts:
        user_liked = False
        if current_user:
            like_check = conn.execute("""
                SELECT id FROM likes WHERE postid = ? AND userid = ?
            """, (post["postid"], current_user["id"])).fetchone()
            user_liked = like_check is not None
        
        posts_with_like_status.append({
            'postid': post['postid'],
            'posttext': post['posttext'],
            'created_at': post['created_at'],
            'username': post['username'],
            'like_count': post['like_count'],
            'user_liked': user_liked
        })
    
    conn.close()
    
    return render_template('home.html', posts=posts_with_like_status)


@app.route('/')
def default():
    if session.get('logged_in'):
        return render_template('home.html')
    return redirect(url_for('login'))

@app.errorhandler(404)
def page_not_found(e):
    if session.get('logged_in'):
        return render_homepage(), 404
    return redirect(url_for('login'))

@app.route('/datadownload')
def datadownload():
    if not session.get('logged_in'):
        flash('You need to log in to download your data.', 'error')
        return redirect(url_for('login'))

    username = session.get('username')
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    
    posts = conn.execute("""
        SELECT postid, posttext, created_at 
        FROM posts 
        WHERE userid = ? 
        ORDER BY created_at DESC
    """, (user["id"],)).fetchall()
    
    likes = conn.execute("""
        SELECT p.postid, p.posttext, l.created_at as liked_at
        FROM likes l
        JOIN posts p ON l.postid = p.postid
        WHERE l.userid = ?
        ORDER BY l.created_at DESC
    """, (user["id"],)).fetchall()
    
    conn.close()

    if not user:
        flash('User data not found.', 'error')
        return redirect(url_for('homepage'))

    user_data = {
        "id": user["id"],
        "username": user["username"],
        "posts": [{"postid": post["postid"], "posttext": post["posttext"], "created_at": post["created_at"]} for post in posts],
        "liked_posts": [{"postid": like["postid"], "posttext": like["posttext"], "liked_at": like["liked_at"]} for like in likes]
    }

    response = app.response_class(
        response=json.dumps(user_data, indent=4),
        status=200,
        mimetype='application/json'
    )
    response.headers['Content-Disposition'] = 'attachment; filename=data.json'
    return response


@app.route('/create_post', methods=['POST'])
def create_post():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    data = request.get_json()
    posttext = data.get('posttext', '').strip()
    
    if not posttext:
        return jsonify({'success': False, 'message': 'Post text cannot be empty'}), 400
    
    if len(posttext) > 500:
        return jsonify({'success': False, 'message': 'Post text too long (max 500 characters)'}), 400
    
    username = session.get('username')
    conn = get_db_connection()
    
    user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    
    if not user:
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO posts (userid, posttext) VALUES (?, ?)",
                (user["id"], sanitize_input(posttext))
            )
            postid = cursor.lastrowid
        
        conn.close()
        return jsonify({
            'success': True, 
            'message': 'Post created successfully',
            'postid': postid
        })
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': 'Error creating post'}), 500

@app.route('/get_posts')
def get_posts():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    username = session.get('username')
    conn = get_db_connection()
    
    user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    
    if not user:
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    posts = conn.execute("""
        SELECT postid, posttext, created_at 
        FROM posts 
        WHERE userid = ? 
        ORDER BY created_at DESC
    """, (user["id"],)).fetchall()
    
    conn.close()
    
    posts_data = [
        {
            'postid': post['postid'],
            'posttext': post['posttext'],
            'created_at': post['created_at']
        }
        for post in posts
    ]
    
    return jsonify({'success': True, 'posts': posts_data})


@app.route('/post/<int:postid>')
def view_post(postid):
    if not session.get('logged_in'):
        flash('You need to log in to view posts.', 'error')
        return redirect(url_for('login'))
    
    username = session.get('username')
    conn = get_db_connection()
    
    post = conn.execute("""
        SELECT p.postid, p.posttext, p.created_at, u.username,
               COUNT(l.id) as like_count
        FROM posts p 
        JOIN users u ON p.userid = u.id 
        LEFT JOIN likes l ON p.postid = l.postid
        WHERE p.postid = ?
        GROUP BY p.postid
    """, (postid,)).fetchone()
    
    if not post:
        conn.close()
        flash('Post not found.', 'error')
        return redirect(url_for('homepage'))
    
    current_user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    user_liked = False
    
    if current_user:
        like_check = conn.execute("""
            SELECT id FROM likes WHERE postid = ? AND userid = ?
        """, (postid, current_user["id"])).fetchone()
        user_liked = like_check is not None
    
    conn.close()
    
    return render_template('post.html', post=post, user_liked=user_liked)


@app.route('/toggle_like', methods=['POST'])
def toggle_like():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    data = request.get_json()
    postid = data.get('postid')
    
    if not postid:
        return jsonify({'success': False, 'message': 'Post ID required'}), 400
    
    username = session.get('username')
    conn = get_db_connection()
    
    user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    post_exists = conn.execute("SELECT postid FROM posts WHERE postid = ?", (postid,)).fetchone()
    if not post_exists:
        conn.close()
        return jsonify({'success': False, 'message': 'Post not found'}), 404
    
    existing_like = conn.execute("""
        SELECT id FROM likes WHERE postid = ? AND userid = ?
    """, (postid, user["id"])).fetchone()
    
    try:
        with conn:
            if existing_like:
                conn.execute("DELETE FROM likes WHERE postid = ? AND userid = ?", 
                           (postid, user["id"]))
                liked = False
                message = "Like removed"
            else:
                conn.execute("INSERT INTO likes (postid, userid) VALUES (?, ?)", 
                           (postid, user["id"]))
                liked = True
                message = "Post liked!"
        
        like_count = conn.execute("""
            SELECT COUNT(*) as count FROM likes WHERE postid = ?
        """, (postid,)).fetchone()["count"]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'liked': liked,
            'like_count': like_count,
            'message': message
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': 'Error toggling like'}), 500


@app.route('/get_like_status/<int:postid>')
def get_like_status(postid):
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    username = session.get('username')
    conn = get_db_connection()
    
    user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    like_count = conn.execute("""
        SELECT COUNT(*) as count FROM likes WHERE postid = ?
    """, (postid,)).fetchone()["count"]
    
    user_liked = conn.execute("""
        SELECT id FROM likes WHERE postid = ? AND userid = ?
    """, (postid, user["id"])).fetchone() is not None
    
    conn.close()
    
    return jsonify({
        'success': True,
        'liked': user_liked,
        'like_count': like_count
    })


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = sanitize_input(request.form['username']).lower()
        password = request.form['password']

        if len(password) < 6:
            flash('Password must be at least 6 characters long!', 'error')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists!', 'error')
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = sanitize_input(request.form['username']).lower()
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.permanent = True
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('homepage'))

        flash('Invalid login credentials!', 'error')

    return render_template('login.html')

@app.route('/home')
def homepage():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_homepage()


@app.route('/logout')
def logout():
    session.clear()  
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(host=host, port=port)
