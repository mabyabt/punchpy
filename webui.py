# admin_gui.py
import os
import sqlite3
import hashlib
import time
import datetime
from functools import wraps
from typing import List, Dict, Optional, Tuple

from nicegui import ui, app
from fastapi import HTTPException, Request

# Database setup
DB_FILE = 'clockinout.db'

# User roles
ROLES = {
    'admin': 'Administrator',
    'viewer': 'Viewer'
}

def setup_admin_database():
    """Create admin tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create admin users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Check if we need to create default admin
    cursor.execute("SELECT COUNT(*) FROM admin_users")
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Create default admin user (username: admin, password: admin123)
        password_hash = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute(
            "INSERT INTO admin_users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", password_hash, "admin")
        )
        print("Created default admin user: admin / admin123")
    
    conn.commit()
    conn.close()

# Authentication helpers
def hash_password(password: str) -> str:
    """Hash a password."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return hash_password(plain_password) == hashed_password

def get_admin_user(username: str) -> Optional[Dict]:
    """Get admin user by username."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, password_hash, role FROM admin_users WHERE username = ?", 
        (username,)
    )
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            'id': user[0],
            'username': user[1],
            'password_hash': user[2],
            'role': user[3]
        }
    return None

# Session management
sessions = {}

def login_required(role=None):
    """Decorator to check if user is logged in."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            session_id = app.storage.user.get('session_id')
            if not session_id or session_id not in sessions:
                ui.open('/login')
                return None
            
            # If role is specified, check if user has required role
            if role and sessions[session_id]['role'] != role:
                ui.notify('You do not have permission to access this feature', type='negative')
                return None
                
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Database operations
def get_users() -> List[Dict]:
    """Get all regular users."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, card_uid, name, created_at FROM users ORDER BY name")
    users = [
        {'id': row[0], 'card_uid': row[1], 'name': row[2], 'created_at': row[3]}
        for row in cursor.fetchall()
    ]
    conn.close()
    return users

def add_user(card_uid: str, name: str) -> bool:
    """Add a new user."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (card_uid, name) VALUES (?, ?)",
            (card_uid, name)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding user: {e}")
        return False

def update_user(user_id: int, card_uid: str, name: str) -> bool:
    """Update an existing user."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET card_uid = ?, name = ? WHERE id = ?",
            (card_uid, name, user_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating user: {e}")
        return False

def delete_user(user_id: int) -> bool:
    """Delete a user."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # First delete related clock events
        cursor.execute("DELETE FROM clock_events WHERE user_id = ?", (user_id,))
        # Then delete the user
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False

def get_clock_events(user_id: Optional[int] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
    """Get clock events with optional filtering."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    query = """
        SELECT c.id, u.name, c.event_type, c.timestamp  
        FROM clock_events c 
        JOIN users u ON c.user_id = u.id 
        WHERE 1=1
    """
    params = []
    
    if user_id:
        query += " AND c.user_id = ?"
        params.append(user_id)
    
    if start_date:
        query += " AND DATE(c.timestamp) >= DATE(?)"
        params.append(start_date)
    
    if end_date:
        query += " AND DATE(c.timestamp) <= DATE(?)"
        params.append(end_date)
    
    query += " ORDER BY c.timestamp DESC LIMIT 1000"
    
    cursor.execute(query, params)
    events = [
        {
            'id': row[0], 
            'name': row[1], 
            'event_type': row[2], 
            'timestamp': row[3]
        }
        for row in cursor.fetchall()
    ]
    conn.close()
    return events

def get_admin_users() -> List[Dict]:
    """Get all admin users."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, role, created_at FROM admin_users ORDER BY username"
    )
    users = [
        {
            'id': row[0], 
            'username': row[1], 
            'role': row[2], 
            'created_at': row[3]
        }
        for row in cursor.fetchall()
    ]
    conn.close()
    return users

def add_admin_user(username: str, password: str, role: str) -> bool:
    """Add a new admin user."""
    try:
        password_hash = hash_password(password)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO admin_users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password_hash, role)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding admin user: {e}")
        return False

def delete_admin_user(user_id: int) -> bool:
    """Delete an admin user."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admin_users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting admin user: {e}")
        return False

# NiceGUI setup
@ui.page('/login')
def login_page():
    """Login page."""
    def try_login():
        username = username_input.value
        password = password_input.value
        
        user = get_admin_user(username)
        if user and verify_password(password, user['password_hash']):
            # Create session
            session_id = hash_password(f"{username}:{time.time()}")
            sessions[session_id] = {
                'username': username,
                'role': user['role'],
                'login_time': time.time()
            }
            app.storage.user['session_id'] = session_id
            
            ui.notify(f'Welcome, {username}!', type='positive')
            ui.open('/')
        else:
            ui.notify('Invalid username or password', type='negative')
    
    with ui.card().classes('w-96 mx-auto mt-16'):
        ui.label('Clock In/Out Admin').classes('text-xl font-bold text-center')
        
        username_input = ui.input('Username').props('outlined').classes('w-full')
        password_input = ui.input('Password', password=True).props('outlined').classes('w-full')
        
        with ui.row().classes('w-full justify-end'):
            ui.button('Login', on_click=try_login).props('color=primary')

@ui.page('/')
def index_page():
    """Main dashboard page."""
    @login_required()
    def load_dashboard():
        session_id = app.storage.user.get('session_id')
        if session_id:
            username = sessions[session_id]['username']
            role = sessions[session_id]['role']
        
        # Header
        with ui.header().classes('flex justify-between items-center'):
            ui.label('Clock In/Out Admin Dashboard').classes('text-xl font-bold')
            
            with ui.row():
                ui.label(f"Logged in as: {username} ({ROLES.get(role, role)})").classes('mr-4')
                ui.button('Logout', on_click=lambda: logout()).classes('bg-red-500 text-white')
        
        # Main content
        with ui.tabs().classes('w-full') as tabs:
            dashboard_tab = ui.tab('Dashboard')
            users_tab = ui.tab('Users')
            reports_tab = ui.tab('Reports')
            admin_tab = ui.tab('Admin Users') if role == 'admin' else None
        
        with ui.tab_panels(tabs, value=dashboard_tab).classes('w-full'):
            with ui.tab_panel(dashboard_tab):
                render_dashboard()
            
            with ui.tab_panel(users_tab):
                render_users_tab()
            
            with ui.tab_panel(reports_tab):
                render_reports_tab()
            
            if admin_tab:
                with ui.tab_panel(admin_tab):
                    render_admin_tab()
        
        # Footer
        with ui.footer():
            ui.label('© 2025 Clock In/Out System').classes('text-xs')
    
    def logout():
        session_id = app.storage.user.get('session_id')
        if session_id and session_id in sessions:
            del sessions[session_id]
        app.storage.user.pop('session_id', None)
        ui.open('/login')
    
    load_dashboard()

def render_dashboard():
    """Render the dashboard tab content."""
    with ui.row().classes('w-full gap-4'):
        # User stats card
        with ui.card().classes('w-1/3'):
            ui.label('Total Users').classes('text-lg font-bold')
            users = get_users()
            ui.label(str(len(users))).classes('text-3xl')
        
        # Today's activity card
        with ui.card().classes('w-1/3'):
            ui.label("Today's Activity").classes('text-lg font-bold')
            today = datetime.date.today().isoformat()
            events = get_clock_events(start_date=today, end_date=today)
            ui.label(str(len(events))).classes('text-3xl')
        
        # System status card
        with ui.card().classes('w-1/3'):
            ui.label('System Status').classes('text-lg font-bold')
            ui.label('Active').classes('text-3xl text-green-500')
    
    # Recent activity
    with ui.card().classes('w-full mt-4'):
        ui.label('Recent Activity').classes('text-lg font-bold')
        
        today = datetime.date.today().isoformat()
        events = get_clock_events(start_date=today, end_date=today)[:10]
        
        with ui.table().props('dense bordered').classes('w-full'):
            ui.table.add_column('Time', 'time')
            ui.table.add_column('Name', 'name')
            ui.table.add_column('Action', 'action')
            
            for event in events:
                event_time = datetime.datetime.fromisoformat(event['timestamp']).strftime('%H:%M:%S')
                action = f"Clocked {event['event_type']}"
                ui.table.add_row(time=event_time, name=event['name'], action=action)

def render_users_tab():
    """Render the users tab content."""
    @login_required(role='admin')
    def handle_add_user():
        if not new_card_uid.value or not new_name.value:
            ui.notify('Please fill in all fields', type='warning')
            return
        
        if add_user(new_card_uid.value, new_name.value):
            ui.notify('User added successfully', type='positive')
            new_card_uid.value = ''
            new_name.value = ''
            refresh_users_table()
        else:
            ui.notify('Failed to add user', type='negative')
    
    @login_required(role='admin')
    def handle_edit_user(user):
        def save_changes():
            if update_user(user['id'], edit_card_uid.value, edit_name.value):
                ui.notify('User updated successfully', type='positive')
                dialog.close()
                refresh_users_table()
            else:
                ui.notify('Failed to update user', type='negative')
        
        with ui.dialog() as dialog, ui.card():
            ui.label('Edit User').classes('text-lg font-bold')
            edit_card_uid = ui.input('Card UID', value=user['card_uid']).props('outlined').classes('w-full')
            edit_name = ui.input('Name', value=user['name']).props('outlined').classes('w-full')
            
            with ui.row().classes('w-full justify-end'):
                ui.button('Cancel', on_click=dialog.close).props('flat')
                ui.button('Save', on_click=save_changes).props('color=primary')
        
        dialog.open()
    
    @login_required(role='admin')
    def handle_delete_user(user):
        def confirm_delete():
            if delete_user(user['id']):
                ui.notify('User deleted successfully', type='positive')
                dialog.close()
                refresh_users_table()
            else:
                ui.notify('Failed to delete user', type='negative')
        
        with ui.dialog() as dialog
        # admin_gui.py (continued)
        with ui.dialog() as dialog, ui.card():
            ui.label(f"Delete User: {user['name']}").classes('text-lg font-bold')
            ui.label('Are you sure you want to delete this user? This will also remove all their clock events.')
            
            with ui.row().classes('w-full justify-end'):
                ui.button('Cancel', on_click=dialog.close).props('flat')
                ui.button('Delete', on_click=confirm_delete).props('color=negative')
        
        dialog.open()
    
    def refresh_users_table():
        users_table.clear()
        users = get_users()
        
        for user in users:
            created_date = datetime.datetime.fromisoformat(user['created_at']).strftime('%Y-%m-%d')
            
            with users_table.add():
                ui.label(user['name'])
                ui.label(user['card_uid'])
                ui.label(created_date)
                
                with ui.row():
                    ui.button(icon='edit', on_click=lambda u=user: handle_edit_user(u)).props('flat')
                    ui.button(icon='delete', on_click=lambda u=user: handle_delete_user(u)).props('flat color=negative')
    
    # Add user form
    with ui.card().classes('w-full'):
        ui.label('Add New User').classes('text-lg font-bold')
        
        with ui.row().classes('w-full items-end gap-4'):
            new_card_uid = ui.input('Card UID').props('outlined').classes('flex-grow')
            new_name = ui.input('Name').props('outlined').classes('flex-grow')
            ui.button('Add User', on_click=handle_add_user).props('color=primary')
    
    # Users table
    with ui.card().classes('w-full mt-4'):
        ui.label('Users').classes('text-lg font-bold')
        
        with ui.grid(columns=4).classes('w-full') as users_table:
            ui.label('Name').classes('font-bold')
            ui.label('Card UID').classes('font-bold')
            ui.label('Created').classes('font-bold')
            ui.label('Actions').classes('font-bold')
        
        refresh_users_table()

def render_reports_tab():
    """Render the reports tab content."""
    users = get_users()
    user_options = [{'label': 'All Users', 'value': None}] + [
        {'label': user['name'], 'value': user['id']} for user in users
    ]
    
    # Filter controls
    with ui.card().classes('w-full'):
        ui.label('Filter Reports').classes('text-lg font-bold')
        
        with ui.row().classes('w-full items-end gap-4'):
            user_filter = ui.select(options=user_options, label='User').props('outlined').classes('flex-grow')
            start_date = ui.date(label='Start Date').props('outlined').classes('flex-grow')
            end_date = ui.date(label='End Date').props('outlined').classes('flex-grow')
            ui.button('Apply Filter', on_click=lambda: refresh_events_table(
                user_filter.value, 
                start_date.value, 
                end_date.value
            )).props('color=primary')
    
    # Events table
    with ui.card().classes('w-full mt-4'):
        ui.label('Clock Events').classes('text-lg font-bold')
        
        with ui.table().props('bordered').classes('w-full') as events_table:
            ui.table.add_column('Date', 'date')
            ui.table.add_column('Time', 'time')
            ui.table.add_column('Name', 'name')
            ui.table.add_column('Action', 'action')
        
        def refresh_events_table(user_id=None, start=None, end=None):
            events_table.rows.clear()
            events = get_clock_events(user_id=user_id, start_date=start, end_date=end)
            
            for event in events:
                dt = datetime.datetime.fromisoformat(event['timestamp'])
                date_str = dt.strftime('%Y-%m-%d')
                time_str = dt.strftime('%H:%M:%S')
                action = f"Clocked {event['event_type']}"
                
                events_table.add_row(date=date_str, time=time_str, name=event['name'], action=action)
        
        # Load initial data
        refresh_events_table()

def render_admin_tab():
    """Render the admin users tab content."""
    @login_required(role='admin')
    def handle_add_admin():
        if not new_username.value or not new_password.value:
            ui.notify('Please fill in all fields', type='warning')
            return
        
        if add_admin_user(new_username.value, new_password.value, new_role.value):
            ui.notify('Admin user added successfully', type='positive')
            new_username.value = ''
            new_password.value = ''
            refresh_admin_table()
        else:
            ui.notify('Failed to add admin user', type='negative')
    
    @login_required(role='admin')
    def handle_delete_admin(user):
        def confirm_delete():
            if delete_admin_user(user['id']):
                ui.notify('Admin user deleted successfully', type='positive')
                dialog.close()
                refresh_admin_table()
            else:
                ui.notify('Failed to delete admin user', type='negative')
        
        # Don't allow deleting yourself
        session_id = app.storage.user.get('session_id')
        current_username = sessions[session_id]['username']
        
        if user['username'] == current_username:
            ui.notify('You cannot delete your own account', type='negative')
            return
        
        with ui.dialog() as dialog, ui.card():
            ui.label(f"Delete Admin: {user['username']}").classes('text-lg font-bold')
            ui.label('Are you sure you want to delete this admin user?')
            
            with ui.row().classes('w-full justify-end'):
                ui.button('Cancel', on_click=dialog.close).props('flat')
                ui.button('Delete', on_click=confirm_delete).props('color=negative')
        
        dialog.open()
    
    def refresh_admin_table():
        admin_table.clear()
        admin_users = get_admin_users()
        
        for user in admin_users:
            created_date = datetime.datetime.fromisoformat(user['created_at']).strftime('%Y-%m-%d')
            
            with admin_table.add():
                ui.label(user['username'])
                ui.label(ROLES.get(user['role'], user['role']))
                ui.label(created_date)
                
                # Don't show delete button for yourself
                session_id = app.storage.user.get('session_id')
                current_username = sessions[session_id]['username']
                
                if user['username'] != current_username:
                    ui.button(icon='delete', on_click=lambda u=user: handle_delete_admin(u)).props('flat color=negative')
                else:
                    ui.label('Current User')
    
    # Add admin form
    with ui.card().classes('w-full'):
        ui.label('Add New Admin User').classes('text-lg font-bold')
        
        with ui.row().classes('w-full items-end gap-4'):
            new_username = ui.input('Username').props('outlined').classes('flex-grow')
            new_password = ui.input('Password', password=True).props('outlined').classes('flex-grow')
            new_role = ui.select(
                options=[{'label': v, 'value': k} for k, v in ROLES.items()],
                label='Role'
            ).props('outlined').classes('flex-grow')
            ui.button('Add Admin', on_click=handle_add_admin).props('color=primary')
    
    # Admin users table
    with ui.card().classes('w-full mt-4'):
        ui.label('Admin Users').classes('text-lg font-bold')
        
        with ui.grid(columns=4).classes('w-full') as admin_table:
            ui.label('Username').classes('font-bold')
            ui.label('Role').classes('font-bold')
            ui.label('Created').classes('font-bold')
            ui.label('Actions').classes('font-bold')
        
        refresh_admin_table()

# Setup the database on startup
setup_admin_database()

# Run the application
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Clock In/Out Admin', host='0.0.0.0', port=8080)
