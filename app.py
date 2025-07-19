import os
import sqlite3
import zipfile
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from your_script import main
from functools import wraps
from datetime import datetime, timedelta
import shutil

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

DB_PATH = 'users.db'
UPLOAD_ROOT = 'uploads'
OUTPUT_ROOT = 'output'
PROFILE_PICS_ROOT = 'profile_pics'
PROGRESS_FILE = 'progress.txt'

# Ensure root folders exist
os.makedirs(UPLOAD_ROOT, exist_ok=True)
os.makedirs(OUTPUT_ROOT, exist_ok=True)
os.makedirs(PROFILE_PICS_ROOT, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            user_type TEXT DEFAULT 'user',
            devices TEXT DEFAULT ''
        )
    ''')
    conn.commit()
    # Ensure admin user exists
    c.execute('SELECT * FROM users WHERE username = ?', ('daqing',))
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, user_type) VALUES (?, ?, ?)",
                  ('daqing', generate_password_hash('dec262024'), 'admin'))
    conn.commit()
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        device_id = request.form.get('device_id')
        remember = request.form.get('remember') == 'on'

        if not device_id:
            flash('Device ID missing. Cannot login.', 'danger')
            return redirect(url_for('login'))

        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()

        if user and check_password_hash(user['password'], password):
            devices = user['devices'].split(',') if user['devices'] else []
            if device_id not in devices:
                if len(devices) >= 2:
                    flash('Device limit reached. Max 2 devices allowed.', 'danger')
                    return redirect(url_for('login'))
                devices.append(device_id)
                conn.execute('UPDATE users SET devices=? WHERE id=?', (','.join(devices), user['id']))
                conn.commit()

            session['user_id'] = user['id']
            session['username'] = user['username']
            session['device_id'] = device_id
            session['user_type'] = user['user_type']
            response = make_response(redirect(url_for('dashboard')))
            if remember:
                expires = datetime.now() + timedelta(days=30)
                response.set_cookie('remember_username', username, expires=expires)
            else:
                response.set_cookie('remember_username', '', expires=0)
            return response
        else:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))

    remembered = request.cookies.get('remember_username', '')
    return render_template('login.html', remembered=remembered)

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Logged out', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user_folder = os.path.join(UPLOAD_ROOT, session['username'])
    output_csv = os.path.join(OUTPUT_ROOT, f"{session['username']}_output.csv")
    profile_folder = os.path.join(PROFILE_PICS_ROOT, session['username'])
    progress_path = os.path.join(user_folder, PROGRESS_FILE)

    os.makedirs(user_folder, exist_ok=True)
    os.makedirs(profile_folder, exist_ok=True)

    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('dashboard'))
        if not file.filename.endswith('.txt'):
            flash('Only .txt files allowed', 'danger')
            return redirect(url_for('dashboard'))

        file_path = os.path.join(user_folder, 'numbers.txt')
        file.save(file_path)

        if os.path.exists(output_csv):
            os.remove(output_csv)
        if os.path.exists(profile_folder):
            shutil.rmtree(profile_folder)
            os.makedirs(profile_folder)
        if os.path.exists(progress_path):
            os.remove(progress_path)

        main(username=session['username'])  # your_script must support this argument

        flash('Scraping completed!', 'success')
        return redirect(url_for('result'))

    return render_template('dashboard.html', username=session.get('username'))

@app.route('/result')
@login_required
def result():
    return render_template('result.html')

@app.route('/download/csv')
@login_required
def download_csv():
    output_csv = os.path.join(OUTPUT_ROOT, f"{session['username']}_output.csv")
    if os.path.exists(output_csv):
        return send_file(output_csv, as_attachment=True)
    flash('No output file found.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/download/photos')
@login_required
def download_photos():
    profile_folder = os.path.join(PROFILE_PICS_ROOT, session['username'])
    zip_path = os.path.join(OUTPUT_ROOT, f"{session['username']}_profile_pics.zip")

    if os.path.exists(profile_folder) and os.listdir(profile_folder):
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for root, _, files in os.walk(profile_folder):
                for file in files:
                    zf.write(os.path.join(root, file), arcname=file)
        return send_file(zip_path, as_attachment=True)

    flash('No profile pictures found.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/progress')
@login_required
def progress():
    progress_path = os.path.join(UPLOAD_ROOT, session['username'], PROGRESS_FILE)
    try:
        with open(progress_path) as f:
            return jsonify({'progress': f.read()})
    except:
        return jsonify({'progress': 'N/A'})

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if session.get('username') != 'daqing':
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db()
    c = conn.cursor()

    if request.method == 'POST':
        new_user = request.form.get('new_username')
        new_pass = request.form.get('new_password')
        if new_user and new_pass:
            try:
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                          (new_user.strip(), generate_password_hash(new_pass)))
                conn.commit()
                flash('User created successfully', 'success')
            except sqlite3.IntegrityError:
                flash('Username already exists', 'danger')

    users = c.execute("SELECT id, username FROM users").fetchall()
    conn.close()
    return render_template('admin.html', users=users)

@app.route('/device_id', methods=['POST'])
def device_id():
    data = request.get_json()
    return jsonify({'status': 'ok'}) if data.get('device_id') else jsonify({'status': 'error'}), 400

if __name__ == '__main__':
    app.run(debug=True)
