import sqlite3
import os
import secrets

DB_PATH = os.path.join(os.path.dirname(__file__), 'bot.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            authorized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN is_super_admin INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS invites (
            code TEXT PRIMARY KEY,
            is_admin_invite INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    try:
        c.execute("ALTER TABLE invites ADD COLUMN is_admin_invite INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    # Set default values if not exists
    c.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('model', 'local-model')")
    c.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('system_prompt', 'You are a helpful assistant.')")
    # Use 127.0.0.1 instead of localhost to avoid IPv6 issues
    c.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('lm_studio_url', 'http://127.0.0.1:1234/v1')")
    
    conn.commit()
    conn.close()

def add_user(user_id, username, is_admin=False, is_super_admin=False):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Maintain existing flags if updating
        c.execute("SELECT is_admin, is_super_admin FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        
        final_is_admin = 1 if is_admin else (row['is_admin'] if row else 0)
        final_is_super = 1 if is_super_admin else (row['is_super_admin'] if row else 0)
        
        c.execute("INSERT OR REPLACE INTO users (user_id, username, is_admin, is_super_admin) VALUES (?, ?, ?, ?)", 
                  (user_id, username, final_is_admin, final_is_super))
        conn.commit()
    finally:
        conn.close()

def make_admin(user_id, is_admin=True):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Prevent demoting super admin
        if not is_admin:
            c.execute("SELECT is_super_admin FROM users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if row and row['is_super_admin']:
                return False # Cannot remove admin from super admin

        c.execute("UPDATE users SET is_admin = ? WHERE user_id = ?", (1 if is_admin else 0, user_id))
        conn.commit()
        return True
    finally:
        conn.close()

def make_super_admin(user_id, is_super=True):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Also set is_admin = 1 if making super admin
        if is_super:
            c.execute("UPDATE users SET is_super_admin = 1, is_admin = 1 WHERE user_id = ?", (user_id,))
        else:
            c.execute("UPDATE users SET is_super_admin = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()

def remove_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT is_super_admin FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        if row and row['is_super_admin']:
            return False # Cannot delete super admin
            
        c.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()

def get_users():
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM users")
        return [dict(row) for row in c.fetchall()]
    finally:
        conn.close()

def is_user_authorized(user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return c.fetchone() is not None
    finally:
        conn.close()

def is_user_admin(user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return row is not None and row['is_admin'] == 1
    finally:
        conn.close()

def is_user_super_admin(user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT is_super_admin FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return row is not None and row['is_super_admin'] == 1
    finally:
        conn.close()

def set_config(key, value):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
    finally:
        conn.close()

def get_config(key, default=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = c.fetchone()
        return row['value'] if row else default
    finally:
        conn.close()

def create_invite(is_admin_invite=False):
    conn = get_connection()
    c = conn.cursor()
    code = secrets.token_hex(4) # 8 chars
    try:
        c.execute("INSERT INTO invites (code, is_admin_invite) VALUES (?, ?)", (code, 1 if is_admin_invite else 0))
        conn.commit()
        return code
    finally:
        conn.close()

def use_invite(code):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Check if invite exists and is within 1 hour validity
        c.execute("""
            SELECT is_admin_invite 
            FROM invites 
            WHERE code = ? 
            AND datetime(created_at) > datetime('now', '-1 hour')
        """, (code,))
        row = c.fetchone()
        
        # If no row found, it might be invalid or expired.
        # Let's clean up expired invites while we are here to keep DB clean
        c.execute("DELETE FROM invites WHERE datetime(created_at) <= datetime('now', '-1 hour')")
        conn.commit()
        
        if not row:
            return None
            
        is_admin = row['is_admin_invite'] == 1
        
        # Consume the invite
        c.execute("DELETE FROM invites WHERE code = ?", (code,))
        conn.commit()
        
        return {"success": True, "is_admin": is_admin}
    finally:
        conn.close()

# Initialize DB on module load (or call it explicitly in main)
init_db()
