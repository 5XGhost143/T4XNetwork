# Imports
import os
import time
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Start Code
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
print(f"{red}Attempting to start Flask server on port 5000...{reset}")
time.sleep(1)
secret_key_pre = os.urandom(25)
print(f"{yellow}your Secret Key for this Session is: {secret_key_pre}{reset}")
time.sleep(3)

app = Flask(__name__)
app.secret_key = secret_key_pre
limiter = Limiter(get_remote_address, app=app)


def get_db_connection():
    conn = sqlite3.connect("users.db")
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
    conn.close()


init_db()


def sanitize_input(input_str):
    return re.sub(r"[^a-zA-Z0-9]", "", input_str)


@app.route('/')
def default():
    if session.get('logged_in'):
        return render_template('homepage.html')
    else:
        return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("20 per 2 minutes")
def register():
    if request.method == 'POST':
        username = sanitize_input(request.form['username'])
        password = request.form['password']

        if len(password) < 6:
            flash('Passwort muss mindestens 6 Zeichen lang sein!', 'error')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            flash('Registrierung erfolgreich! Du kannst dich jetzt einloggen.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Benutzername existiert bereits!', 'error')
            return redirect(url_for('register'))
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per 2 minutes")
def login():
    if request.method == 'POST':
        username = sanitize_input(request.form['username'])
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('homepage'))
        else:
            flash('Invalid login credentials.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/homepage')
@limiter.limit("500 per 2 minutes")
def homepage():
    if session.get('logged_in'):
        return render_template('homepage.html')
    else:
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run()
