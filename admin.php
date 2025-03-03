<?php
// Database configuration
$db_file = 'clockinout.db';
$dsn = 'sqlite:' . $db_file;

// Establish database connection
try {
    $pdo = new PDO($dsn);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    die("Connection failed: " . $e->getMessage());
}

// Handle form submissions
if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    // Add new user
    if (isset($_POST['add_user'])) {
        $card_uid = trim($_POST['card_uid']);
        $name = trim($_POST['name']);
        
        // Validate input
        $errors = [];
        if (empty($card_uid)) {
            $errors[] = "Card UID is required";
        } elseif (strlen($card_uid) < 2 || strlen($card_uid) > 64) {
            $errors[] = "Card UID must be between 2 and 64 characters";
        }
        
        if (empty($name)) {
            $errors[] = "Name is required";
        }
        
        // If no errors, add user to database
        if (empty($errors)) {
            try {
                $stmt = $pdo->prepare("INSERT INTO users (card_uid, name) VALUES (?, ?)");
                $stmt->execute([$card_uid, $name]);
                $success_message = "User added successfully!";
            } catch (PDOException $e) {
                if ($e->getCode() == 23000) { // SQLITE_CONSTRAINT violation
                    $errors[] = "Card UID already exists";
                } else {
                    $errors[] = "Error adding user: " . $e->getMessage();
                }
            }
        }
    }
    
    // Handle manual clock in/out
    if (isset($_POST['manual_clock'])) {
        $user_id = $_POST['user_id'];
        $event_type = $_POST['event_type'];
        
        try {
            $stmt = $pdo->prepare("INSERT INTO clock_events (user_id, event_type) VALUES (?, ?)");
            $stmt->execute([$user_id, $event_type]);
            $success_message = "Clock event recorded successfully!";
        } catch (PDOException $e) {
            $errors[] = "Error recording event: " . $e->getMessage();
        }
    }
}

// Get users for display
$users = [];
try {
    $stmt = $pdo->query("SELECT id, card_uid, name, created_at FROM users ORDER BY name");
    $users = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    $errors[] = "Error retrieving users: " . $e->getMessage();
}

// Get recent clock events
$events = [];
try {
    $stmt = $pdo->query("
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
    ");
    $events = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    $errors[] = "Error retrieving events: " . $e->getMessage();
}

// Calculate statistics
$stats = [];
try {
    // Total users
    $stmt = $pdo->query("SELECT COUNT(*) FROM users");
    $stats['total_users'] = $stmt->fetchColumn();
    
    // Total events
    $stmt = $pdo->query("SELECT COUNT(*) FROM clock_events");
    $stats['total_events'] = $stmt->fetchColumn();
    
    // Currently clocked in users
    $stmt = $pdo->query("
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
    ");
    $stats['clocked_in'] = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    $errors[] = "Error calculating statistics: " . $e->getMessage();
}

// Get current datetime for display
$current_datetime = date('Y-m-d H:i:s');
?>
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
        <p>Current time: <?php echo $current_datetime; ?></p>
        
        <?php if (!empty($success_message)): ?>
            <div class="alert alert-success">
                <?php echo $success_message; ?>
            </div>
        <?php endif; ?>
        
        <?php if (!empty($errors)): ?>
            <div class="alert alert-danger">
                <ul>
                    <?php foreach ($errors as $error): ?>
                        <li><?php echo $error; ?></li>
                    <?php endforeach; ?>
                </ul>
            </div>
        <?php endif; ?>
        
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
                    <div class="stat-value"><?php echo $stats['total_users']; ?></div>
                </div>
                <div class="stat-card">
                    <h3>Total Events</h3>
                    <div class="stat-value"><?php echo $stats['total_events']; ?></div>
                </div>
                <div class="stat-card">
                    <h3>Currently Clocked In</h3>
                    <div class="stat-value"><?php echo count($stats['clocked_in']); ?></div>
                </div>
            </div>
            
            <div class="card">
                <h2>Currently Clocked In Users</h2>
                <?php if (empty($stats['clocked_in'])): ?>
                    <p>No users currently clocked in.</p>
                <?php else: ?>
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Name</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($stats['clocked_in'] as $user): ?>
                                <tr>
                                    <td><?php echo $user['id']; ?></td>
                                    <td><?php echo htmlspecialchars($user['name']); ?></td>
                                    <td>
                                        <form method="post" style="display: inline;">
                                            <input type="hidden" name="user_id" value="<?php echo $user['id']; ?>">
                                            <input type="hidden" name="event_type" value="out">
                                            <button type="submit" name="manual_clock" class="btn">Clock Out</button>
                                        </form>
                                    </td>
                                </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                <?php endif; ?>
            </div>
            
            <div class="card">
                <h2>Recent Events</h2>
                <?php if (empty($events)): ?>
                    <p>No events recorded yet.</p>
                <?php else: ?>
                    <table>
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>User</th>
                                <th>Event</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach (array_slice($events, 0, 10) as $event): ?>
                                <tr>
                                    <td><?php echo $event['timestamp']; ?></td>
                                    <td><?php echo htmlspecialchars($event['name']); ?></td>
                                    <td>
                                        <?php if ($event['event_type'] == 'in'): ?>
                                            <span class="badge badge-success">Clock In</span>
                                        <?php else: ?>
                                            <span class="badge badge-danger">Clock Out</span>
                                        <?php endif; ?>
                                    </td>
                                </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                <?php endif; ?>
            </div>
        </div>
        
        <!-- Users Tab -->
        <div id="users" class="tab-content">
            <div class="card">
                <h2>All Users</h2>
                <?php if (empty($users)): ?>
                    <p>No users found. Add a new user to get started.</p>
                <?php else: ?>
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
                            <?php foreach ($users as $user): ?>
                                <tr>
                                    <td><?php echo $user['id']; ?></td>
                                    <td><?php echo htmlspecialchars($user['name']); ?></td>
                                    <td><?php echo htmlspecialchars($user['card_uid']); ?></td>
                                    <td><?php echo $user['created_at']; ?></td>
                                    <td>
                                        <form method="post" style="display: inline;">
                                            <input type="hidden" name="user_id" value="<?php echo $user['id']; ?>">
                                            <input type="hidden" name="event_type" value="in">
                                            <button type="submit" name="manual_clock" class="btn">Clock In</button>
                                        </form>
                                        <form method="post" style="display: inline; margin-left: 5px;">
                                            <input type="hidden" name="user_id" value="<?php echo $user['id']; ?>">
                                            <input type="hidden" name="event_type" value="out">
                                            <button type="submit" name="manual_clock" class="btn">Clock Out</button>
                                        </form>
                                    </td>
                                </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                <?php endif; ?>
            </div>
        </div>
        
        <!-- Events Tab -->
        <div id="events" class="tab-content">
            <div class="card">
                <h2>All Recent Events</h2>
                <?php if (empty($events)): ?>
                    <p>No events recorded yet.</p>
                <?php else: ?>
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
                            <?php foreach ($events as $event): ?>
                                <tr>
                                    <td><?php echo $event['id']; ?></td>
                                    <td><?php echo $event['timestamp']; ?></td>
                                    <td><?php echo htmlspecialchars($event['name']); ?></td>
                                    <td>
                                        <?php if ($event['event_type'] == 'in'): ?>
                                            <span class="badge badge-success">Clock In</span>
                                        <?php else: ?>
                                            <span class="badge badge-danger">Clock Out</span>
                                        <?php endif; ?>
                                    </td>
                                </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                <?php endif; ?>
            </div>
        </div>
        
        <!-- Add User Tab -->
        <div id="add-user" class="tab-content">
            <div class="card">
                <h2>Add New User</h2>
                <form method="post">
                    <div class="form-group">
                        <label for="card_uid">Card UID:</label>
                        <input type="text" id="card_uid" name="card_uid" placeholder="Enter card UID (2-64 characters)" required>
                    </div>
                    <div class="form-group">
                        <label for="name">Name:</label>
                        <input type="text" id="name" name="name" placeholder="Enter user name" required>
                    </div>
                    <button type="submit" name="add_user" class="btn">Add User</button>
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
