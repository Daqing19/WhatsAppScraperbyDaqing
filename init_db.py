import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = 'users.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    # Optional: Add an admin account if not exists
    admin_username = 'daqing'
    admin_password = generate_password_hash('dec262024')
    c.execute("SELECT * FROM users WHERE username=?", (admin_username,))
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, user_type) VALUES (?, ?, ?)",
                  (admin_username, admin_password, 'admin'))
    conn.commit()
    conn.close()
    print("Database initialized.")

if __name__ == '__main__':
    init_db()
