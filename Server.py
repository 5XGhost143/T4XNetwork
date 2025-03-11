# Imports

import os
import time
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
limiter = Limiter(
    get_remote_address,
    app=app
)


# Beispielhafte Benutzerdaten mit gehashten Passwörtern
VALID_USERS = {
    "ghost143": generate_password_hash("james"),
    "user1": generate_password_hash("mypassword")
}

# Funktion zur Bereinigung der Eingaben (eventuell nur für den Benutzernamen sinnvoll)
def sanitize_input(input_str):
    return re.sub(r"[^a-zA-Z0-9 ]", "", input_str)

@app.route('/')
def default():
    if session.get('logged_in'):
        return render_template('homepage.html')
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per 5 minutes")
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Eingaben bereinigen
        username = sanitize_input(username)
        password = sanitize_input(password)

        if username in VALID_USERS and check_password_hash(VALID_USERS[username], password):
            session['logged_in'] = True
            session['username'] = username  # Speichert den Benutzernamen in der Session
            print("Login erfolgreich, Sitzung gesetzt")  # Debug-Ausgabe
            return redirect(url_for('homepage'))
        else:
            flash('Invalid login credentials.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')  # Login-Seite für GET-Anfrage



@app.route('/homepage')
@limiter.limit("500 per 2 minutes")
def homepage():
    if session.get('logged_in'):
        return render_template('homepage.html')
    else:
        return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run()