import os
import time
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta
import json

with open("config/flask_config.json") as config_file:
    config = json.load(config_file)

port = config.get("port", 5000)

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
print(f"{red}Attempting to start Flask server on port {port}...{reset}")
time.sleep(1)
secret_key_pre = os.urandom(25)
print(f"{yellow}Your Secret Key for this Web Session is: {secret_key_pre}{reset}")
time.sleep(3)

app = Flask(__name__)
app.secret_key = secret_key_pre
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

limiter = Limiter(get_remote_address, app=app)


def get_db_connection():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn


# Initialize Database
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
    conn.close()


init_db()


# Input Validation
def sanitize_input(input_str):
    return re.sub(r"[^a-zA-Z0-9]", "", input_str)


# Default Route (Redirect based on login status)
@app.route('/')
def default():
    if session.get('logged_in'):
        return render_template('homepage.html')
    return redirect(url_for('login'))


@app.route('/datadownload')
@limiter.limit("10 per hour")  # Begrenzung, um Missbrauch zu vermeiden
def datadownload():
    if not session.get('logged_in'):
        flash('You need to log in to download your data.', 'error')
        return redirect(url_for('login'))

    username = session.get('username')
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    if not user:
        flash('User data not found.', 'error')
        return redirect(url_for('homepage'))

    user_data = {
        "id": user["id"],
        "username": user["username"],
    }

    response = app.response_class(
        response=json.dumps(user_data, indent=4),
        status=200,
        mimetype='application/json'
    )
    response.headers['Content-Disposition'] = 'attachment; filename=data.json'
    return response


@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("20 per 2 minutes")
def register():
    if request.method == 'POST':
        username = sanitize_input(request.form['username']).lower()  # Kleinbuchstaben speichern
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
@limiter.limit("20 per 2 minutes")
def login():
    if request.method == 'POST':
        username = sanitize_input(request.form['username']).lower()
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.permanent = True  # Persistent session
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('homepage'))

        flash('Invalid login credentials!', 'error')

    return render_template('login.html')



# Homepage (Only for Logged-in Users)
@app.route('/homepage')
@limiter.limit("500 per 2 minutes")
def homepage():
    if session.get('logged_in'):
        return render_template('homepage.html')
    return redirect(url_for('login'))


# Logout (Clear Session)
@app.route('/logout')
def logout():
    session.clear()  # Clear entire session
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(port=port)
