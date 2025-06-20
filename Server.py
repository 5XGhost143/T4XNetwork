import os
import time
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
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
    conn.close()


init_db()

def sanitize_input(user_input):
    return escape(user_input)


@app.route('/')
def default():
    if session.get('logged_in'):
        return render_template('homepage.html')
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
    
    conn.close()

    if not user:
        flash('User data not found.', 'error')
        return redirect(url_for('homepage'))

    user_data = {
        "id": user["id"],
        "username": user["username"],
        "posts": [{"postid": post["postid"], "posttext": post["posttext"], "created_at": post["created_at"]} for post in posts]
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



@app.route('/homepage')
def homepage():
    if session.get('logged_in'):
        return render_template('homepage.html')
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()  
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(host=host, port=port)