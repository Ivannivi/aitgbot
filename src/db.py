import sqlite3
import os
import secrets
import json
import logging
from datetime import datetime, timedelta

# Store database in project root (parent of src directory)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot.db')

logger = logging.getLogger(__name__)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================================
# SCHEMALESS DATABASE
# ============================================================================
# All data is stored as JSON documents in a single 'documents' table.
# Each document has a collection name (like 'users', 'config', 'invites')
# and a unique key within that collection.
# No migrations needed - just add new fields to documents as needed.
# ============================================================================

def init_db():
    """Initialize the schemaless document store"""
    conn = get_connection()
    c = conn.cursor()
    
    # Single table for all documents
    c.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            collection TEXT NOT NULL,
            doc_key TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (collection, doc_key)
        )
    ''')
    
    # Index for faster collection queries
    c.execute('CREATE INDEX IF NOT EXISTS idx_collection ON documents(collection)')
    
    conn.commit()
    conn.close()
    
    # Set default config values if not exist
    if get_doc('config', 'model') is None:
        set_doc('config', 'model', {'value': 'local-model'})
    if get_doc('config', 'system_prompt') is None:
        set_doc('config', 'system_prompt', {'value': 'You are a helpful assistant.'})
    if get_doc('config', 'lm_studio_url') is None:
        set_doc('config', 'lm_studio_url', {'value': 'http://127.0.0.1:1234/v1'})


# ============================================================================
# CORE DOCUMENT OPERATIONS
# ============================================================================

def set_doc(collection, key, data):
    """Store a document in a collection"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT OR REPLACE INTO documents (collection, doc_key, data, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (collection, str(key), json.dumps(data)))
        conn.commit()
    finally:
        conn.close()


def get_doc(collection, key):
    """Retrieve a document from a collection"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            'SELECT data FROM documents WHERE collection = ? AND doc_key = ?',
            (collection, str(key))
        )
        row = c.fetchone()
        return json.loads(row['data']) if row else None
    finally:
        conn.close()


def delete_doc(collection, key):
    """Delete a document from a collection"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            'DELETE FROM documents WHERE collection = ? AND doc_key = ?',
            (collection, str(key))
        )
        conn.commit()
        return c.rowcount > 0
    finally:
        conn.close()


def get_all_docs(collection):
    """Get all documents in a collection"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            'SELECT doc_key, data, created_at FROM documents WHERE collection = ?',
            (collection,)
        )
        return [
            {'key': row['doc_key'], 'created_at': row['created_at'], **json.loads(row['data'])}
            for row in c.fetchall()
        ]
    finally:
        conn.close()


def update_doc(collection, key, updates):
    """Update specific fields in a document (merges with existing data)"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            'SELECT data FROM documents WHERE collection = ? AND doc_key = ?',
            (collection, str(key))
        )
        row = c.fetchone()
        if row:
            data = json.loads(row['data'])
            data.update(updates)
            c.execute('''
                UPDATE documents SET data = ?, updated_at = CURRENT_TIMESTAMP
                WHERE collection = ? AND doc_key = ?
            ''', (json.dumps(data), collection, str(key)))
            conn.commit()
            return True
        return False
    finally:
        conn.close()


# ============================================================================
# USER FUNCTIONS
# ============================================================================

def add_user(user_id, username, is_admin=False, is_super_admin=False):
    existing = get_doc('users', user_id)
    
    data = {
        'user_id': user_id,
        'username': username,
        'is_admin': is_admin or (existing.get('is_admin', False) if existing else False),
        'is_super_admin': is_super_admin or (existing.get('is_super_admin', False) if existing else False),
    }
    
    set_doc('users', user_id, data)


def make_admin(user_id, is_admin=True):
    user = get_doc('users', user_id)
    if not user:
        return False
    
    # Prevent demoting super admin
    if not is_admin and user.get('is_super_admin'):
        return False
    
    return update_doc('users', user_id, {'is_admin': is_admin})


def make_super_admin(user_id, is_super=True):
    user = get_doc('users', user_id)
    if not user:
        return False
    
    updates = {'is_super_admin': is_super}
    if is_super:
        updates['is_admin'] = True
    
    return update_doc('users', user_id, updates)


def remove_user(user_id):
    user = get_doc('users', user_id)
    if user and user.get('is_super_admin'):
        return False  # Cannot delete super admin
    
    return delete_doc('users', user_id)


def get_users():
    return get_all_docs('users')


def is_user_authorized(user_id):
    return get_doc('users', user_id) is not None


def is_user_admin(user_id):
    user = get_doc('users', user_id)
    return user is not None and user.get('is_admin', False)


def is_user_super_admin(user_id):
    user = get_doc('users', user_id)
    return user is not None and user.get('is_super_admin', False)


# ============================================================================
# CONFIG FUNCTIONS
# ============================================================================

def set_config(key, value):
    set_doc('config', key, {'value': value})


def get_config(key, default=None):
    doc = get_doc('config', key)
    return doc.get('value', default) if doc else default


# ============================================================================
# INVITE FUNCTIONS
# ============================================================================

def create_invite(is_admin_invite=False):
    code = secrets.token_hex(4)  # 8 chars
    set_doc('invites', code, {'is_admin_invite': is_admin_invite})
    return code


def use_invite(code):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Get invite if exists and not expired (within 1 hour)
        c.execute('''
            SELECT data, created_at FROM documents 
            WHERE collection = 'invites' AND doc_key = ?
        ''', (code,))
        row = c.fetchone()
        
        # Clean up expired invites
        c.execute('''
            DELETE FROM documents 
            WHERE collection = 'invites' 
            AND datetime(created_at) <= datetime('now', '-1 hour')
        ''')
        conn.commit()
        
        if not row:
            return None
        
        # Check if expired
        created_at = datetime.fromisoformat(row['created_at'].replace(' ', 'T'))
        if datetime.now() - created_at > timedelta(hours=1):
            delete_doc('invites', code)
            return None
        
        data = json.loads(row['data'])
        is_admin = data.get('is_admin_invite', False)
        
        # Consume the invite
        delete_doc('invites', code)
        
        return {"success": True, "is_admin": is_admin}
    finally:
        conn.close()


# Initialize DB on module load
init_db()
