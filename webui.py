import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g, flash
from datetime import datetime
import secrets

# Configuration
DB_FILE = 'clockinout.db'
HOST = '0.0.0.0'  # Accessible from any network interface
PORT = 5000
DEBUG = True  # Set to False in production
SECRET_KEY = secrets.token_hex(16)  # Generate a random secret key

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

# Ensure the template directory exists
os.makedirs('templates', exist_ok=True)

# Create the HTML template
admin_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clock In/Out Admin Interface</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        h1, h2, h3 {
            color: #2c3e50;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .card {
            background: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: #f8f9fa;
            border-left: 4px solid #4e73df;
            padding: 15px;
            border-radius: 5px;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f8f9fa;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }
        .badge-success {
            background-color: #28a745;
            color: white;
        }
        .badge-danger {
            background-color: #dc3545;
            color: white;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .btn {
            display: inline-block;
            padding: 8px 15px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .btn:hover {
            background: #2980b9;
        }
        .alert {
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        .alert-success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert-danger {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .tabs {
            display: flex;
            border-bottom: 1px solid #ddd;
            margin-bottom: 20px;
        }
        .tab {
            padding: 10px 15px;
            cursor: pointer;
            margin-right: 5px;
        }
        .tab.active {
            border-bottom: 2px solid #3498db;
            font-weight: bold;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Clock In/Out Admin Interface</h1>
        <p>Current time: {{ current_datetime }}</p>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <div class="tabs">
            <div class="tab active" data-tab="dashboard">Dashboard</div>
            <div class="tab" data-tab="users">Users</div>
            <div class="tab" data-tab="events">Recent Events</div>
            <div class="tab" data-tab="add-user">Add New User</div>
        </div>
        
        <!-- Dashboard Tab -->
        <div id="dashboard" class="tab-content active">
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Total Users</h3>
                    <div class="stat-value">{{ stats.total_users }}</div>
                </div>
                <div class="stat-card">
                    <h3>Total Events</h3>
                    <div class="stat-value">{{ stats.total_events }}</div>
                </div>
                <div class="stat-card">
                    <h3>Currently Clocked In</h3>
                    <div class="stat-value">{{ stats.clocked_in|length }}</div>
                </div>
            </div>
            
            <div class="card">
                <h2>Currently Clocked In Users</h2>
                {% if stats.clocked_in|length == 0 %}
                    <p>No users currently clocked in.</p>
                {% else %}
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Name</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for user in stats.clocked_in %}
                                <tr>
                                    <td>{{ user.id }}</td>
                                    <td>{{ user.name }}</td>
                                    <td>
                                        <form method="post" action="{{ url_for('manual_clock') }}" style="display: inline;">
                                            <input type="hidden" name="user_id" value="{{ user.id }}">
                                            <input type="hidden" name="event_type" value="out">
                                            <button type="submit" class="btn">Clock Out</button>
                                        </form>
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% endif %}
            </div>
            
            <div class="card">
                <h2>Recent Events</h2>
                {% if events|length == 0 %}
                    <p>No events recorded yet.</p>
                {% else %}
                    <table>
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>User</th>
                                <th>Event</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for event in events[:10] %}
                                <tr>
                                    <td>{{ event.timestamp }}</td>
                                    <td>{{ event.name }}</td>
                                    <td>
                                        {% if event.event_type == 'in' %}
                                            <span class="badge badge-success">Clock In</span>
                                        {% else %}
                                            <span class="badge badge-danger">Clock Out</span>
                                        {% endif %}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% endif %}
            </div>
        </div>
        
        <!-- Users Tab -->
        <div id="users" class="tab-content">
            <div class="card">
                <h2>All Users</h2>
                {% if users|length == 0 %}
                    <p>No users found. Add a new user to get started.</p>
                {% else %}
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Name</th>
                                <th>Card UID</th>
                                <th>Created On</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for user in users %}
                                <tr>
                                    <td>{{ user.id }}</td>
                                    <td>{{ user.name }}</td>
                                    <td>{{ user.card_uid }}</td>
                                    <td>{{ user.created_at }}</td>
                                    <td>
                                        <form method="post" action="{{ url_for('manual_clock') }}" style="display: inline;">
                                            <input type="hidden" name="user_id" value="{{ user.id }}">
                                            <input type="hidden" name="event_type" value="in">
                                            <button type="submit" class="btn">Clock In</button>
                                        </form>
                                        <form method="post" action="{{ url_for('manual_clock') }}" style="display: inline; margin-left: 5px;">
                                            <input type="hidden" name="user_id" value="{{ user.id }}">
                                            <input type="hidden" name="event_type" value="out">
                                            <button type="submit" class="btn">Clock Out</button>
                                        </form>
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% endif %}
            </div>
        </div>
        
        <!-- Events Tab -->
        <div id="events" class="tab-content">
            <div class="card">
                <h2>All Recent Events</h2>
                {% if events|length == 0 %}
                    <p>No events recorded yet.</p>
                {% else %}
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Time</th>
                                <th>User</th>
                                <th>Event</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for event in events %}
                                <tr>
                                    <td>{{ event.id }}</td>
                                    <td>{{ event.timestamp }}</td>
                                    <td>{{ event.name }}</td>
                                    <td>
                                        {% if event.event_type == 'in' %}
                                            <span class="badge badge-success">Clock In</span>
                                        {% else %}
                                            <span class="badge badge-danger">Clock Out</span>
                                        {% endif %}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% endif %}
            </div>
        </div>
        
        <!-- Add User Tab -->
        <div id="add-user" class="tab-content">
            <div class="card">
                <h2>Add New User</h2>
                <form method="post" action="{{ url_for('add_user') }}">
                    <div class="form-group">
                        <label for="card_uid">Card UID:</label>
                        <input type="text" id="card_uid" name="card_uid" placeholder="Enter card UID (2-64 characters)" required>
                    </div>
                    <div class="form-group">
                        <label for="name">Name:</label>
                        <input type="text" id="name" name="name" placeholder="Enter user name" required>
                    </div>
                    <button type="submit" class="btn">Add User</button>
                </form>
            </div>
        </div>
    </div>
    
    <script>
        // Simple tab functionality
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                // Hide all tab contents
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                
                // Deactivate all tabs
                document.querySelectorAll('.tab').forEach(t => {
                    t.classList.remove('active');
                });
                
                // Activate clicked tab
                tab.classList.add('active');
                
                // Show corresponding content
                const tabId = tab.getAttribute('data-tab');
                document.getElementById(tabId).classList.add('active');
            });
        });
    </script>
</body>
</html>
'''

# Write the template to a file
with open('templates/admin.html', 'w') as f:
    f.write(admin_template)

# Database helper functions
def get_db():
    """Get database connection"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_FILE)
        db.row_factory = sqlite3.Row  # This enables column access by name
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Close database connection when app context ends"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """Query the database"""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def modify_db(query, args=()):
    """Modify the database (insert, update, delete)"""
    conn = get_db()
    try:
        conn.execute(query, args)
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False

# Validate card UID format
def validate_card_uid(card_uid):
    """Validate that card UID is not empty and has a reasonable length."""
    if not card_uid:
        return False
    
    # Only check that UID is not too long or too short
    if len(card_uid) < 2 or len(card_uid) > 64:
        return False
    
    return True

# Routes
@app.route('/')
def index():
    """Main admin interface page"""
    # Get users
    users = query_db("SELECT id, card_uid, name, created_at FROM users ORDER BY name")
    
    # Get recent events
    events = query_db("""
        SELECT 
            c.id, 
            u.name, 
            c.event_type, 
            c.timestamp 
        FROM 
            clock_events c 
            JOIN users u ON c.user_id = u.id 
        ORDER BY 
            c.timestamp DESC 
        LIMIT 50
    """)
    
    # Calculate statistics
    stats = {}
    stats['total_users'] = query_db("SELECT COUNT(*) FROM users", one=True)[0]
    stats['total_events'] = query_db("SELECT COUNT(*) FROM clock_events", one=True)[0]
    
    # Currently clocked in users
    stats['clocked_in'] = query_db("""
        SELECT 
            u.id, 
            u.name,
            (
                SELECT event_type 
                FROM clock_events 
                WHERE user_id = u.id 
                ORDER BY timestamp DESC 
                LIMIT 1
            ) as last_event
        FROM 
            users u
        HAVING 
            last_event = 'in'
    """)
    
    # Get current datetime for display
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('admin.html', 
                          users=users, 
                          events=events, 
                          stats=stats, 
                          current_datetime=current_datetime)

@app.route('/add_user', methods=['POST'])
def add_user():
    """Add a new user"""
    card_uid = request.form.get('card_uid', '').strip()
    name = request.form.get('name', '').strip()
    
    # Validate input
    if not validate_card_uid(card_uid):
        flash("Card UID must be between 2 and 64 characters", "danger")
        return redirect(url_for('index'))
    
    if not name:
        flash("Name is required", "danger")
        return redirect(url_for('index'))
    
    # Try to add the user
    success = modify_db(
        "INSERT INTO users (card_uid, name) VALUES (?, ?)",
        (card_uid, name)
    )
    
    if success:
        flash("User added successfully!", "success")
    else:
        flash("Error adding user. Card UID might already exist.", "danger")
    
    return redirect(url_for('index'))

@app.route('/manual_clock', methods=['POST'])
def manual_clock():
    """Manually clock a user in or out"""
    user_id = request.form.get('user_id')
    event_type = request.form.get('event_type')
    
    if not user_id or event_type not in ['in', 'out']:
        flash("Invalid request", "danger")
        return redirect(url_for('index'))
    
    success = modify_db(
        "INSERT INTO clock_events (user_id, event_type) VALUES (?, ?)",
        (user_id, event_type)
    )
    
    if success:
        user = query_db("SELECT name FROM users WHERE id = ?", (user_id,), one=True)
        flash(f"{user['name']} clocked {event_type} successfully!", "success")
    else:
        flash("Error recording clock event", "danger")
    
    return redirect(url_for('index'))

# Ensure database is set up
def setup_database():
    """Ensure database and tables exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        card_uid TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create clock events table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clock_events (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # Set up the database
    setup_database()
    
    # Run the app
    print(f"Starting Clock In/Out Admin Interface at http://{HOST}:{PORT}")
    print("Press Ctrl+C to quit")
    app.run(host=HOST, port=PORT, debug=DEBUG)
