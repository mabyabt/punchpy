import os
import sqlite3
import datetime
import time
import threading
from typing import List, Tuple, Optional

# Database setup
DB_FILE = 'clockinout.db'

def setup_database():
    """Create database and tables if they don't exist."""
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

# User management
def add_user(card_uid: str, name: str) -> bool:
    """Add a new user to the database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (card_uid, name) VALUES (?, ?)", (card_uid, name))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        print(f"Error: Card UID '{card_uid}' already exists.")
        return False
    except Exception as e:
        print(f"Error adding user: {e}")
        return False

def get_user_by_card(card_uid: str) -> Optional[Tuple[int, str]]:
    """Get user ID and name by card UID."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM users WHERE card_uid = ?", (card_uid,))
    user = cursor.fetchone()
    conn.close()
    return user if user else None

def list_all_users() -> List[Tuple[int, str, str]]:
    """Get list of all users."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, card_uid, name FROM users")
    users = cursor.fetchall()
    conn.close()
    return users

# Clock events
def record_clock_event(user_id: int, event_type: str) -> bool:
    """Record a clock in/out event."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO clock_events (user_id, event_type) VALUES (?, ?)",
            (user_id, event_type)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error recording event: {e}")
        return False

def get_last_event(user_id: int) -> Optional[str]:
    """Get the last event type for a user."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT event_type FROM clock_events WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1",
        (user_id,)
    )
    last_event = cursor.fetchone()
    conn.close()
    return last_event[0] if last_event else None

def get_user_events(user_id: int, limit: int = 10) -> List[Tuple[str, str]]:
    """Get recent events for a specific user."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT event_type, timestamp FROM clock_events WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit)
    )
    events = cursor.fetchall()
    conn.close()
    return events

def get_all_events(limit: int = 20) -> List[Tuple[str, str, str]]:
    """Get recent events for all users."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT u.name, c.event_type, c.timestamp 
        FROM clock_events c 
        JOIN users u ON c.user_id = u.id 
        ORDER BY c.timestamp DESC 
        LIMIT ?
        """,
        (limit,)
    )
    events = cursor.fetchall()
    conn.close()
    return events

# RFID reader simulation
class RFIDReader:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the RFID reader thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._read_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """Stop the RFID reader thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
    
    def _read_loop(self):
        """Background thread that simulates RFID scanning."""
        print("\nRFID reader activated. Waiting for cards...")
        print("(To simulate a card scan, enter 'scan' followed by the card UID)")
        
        while self.running:
            time.sleep(0.5)  # Reduce CPU usage

    def process_scan(self, card_uid: str):
        """Process a card scan."""
        user = get_user_by_card(card_uid)
        
        if not user:
            print(f"\nUnknown card UID: {card_uid}")
            return
        
        user_id, name = user
        last_event = get_last_event(user_id)
        
        # Toggle between clock in/out
        event_type = "out" if last_event == "in" else "in"
        
        if record_clock_event(user_id, event_type):
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{current_time}] {name} clocked {event_type}!")
        else:
            print(f"\nFailed to record clock event for {name}")

# Validate card UID format
def validate_card_uid(card_uid: str) -> bool:
    """
    Validate that card UID is not empty and has a reasonable length.
    Accepts all characters including special characters like 'ö'.
    """
    if not card_uid:
        return False
    
    # Only check that UID is not too long or too short
    if len(card_uid) < 2 or len(card_uid) > 64:
        return False
    
    return True

# Command line interface
def print_header():
    """Print application header."""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 60)
    print("                 CLOCK IN/OUT SYSTEM DEMO")
    print("=" * 60)
    print("\nCommands:")
    print("  1. Add User              2. List Users")
    print("  3. View Recent Events    4. Start RFID Scanner")
    print("  5. Exit")
    print("\nEnter a command number:")

def main():
    """Main application function."""
    setup_database()
    rfid_reader = RFIDReader()
    
    while True:
        print_header()
        choice = input("> ").strip()
        
        if choice == "1":
            # Add User
            print("\n--- ADD USER ---")
            print("Enter Card UID (can include special characters like 'öö122ö8333'):")
            card_uid = input("> ").strip()
            
            if not validate_card_uid(card_uid):
                print("Invalid UID format. UID must be between 2 and 64 characters.")
                input("\nPress Enter to continue...")
                continue
                
            name = input("Enter User Name: ").strip()
            if not name:
                print("Name cannot be empty.")
                input("\nPress Enter to continue...")
                continue
                
            if add_user(card_uid, name):
                print(f"\nUser '{name}' with Card UID '{card_uid}' added successfully!")
            input("\nPress Enter to continue...")
            
        elif choice == "2":
            # List Users
            print("\n--- USER LIST ---")
            users = list_all_users()
            if users:
                print(f"{'ID':<5} {'Card UID':<25} {'Name':<30}")
                print("-" * 60)
                for user_id, card_uid, name in users:
                    print(f"{user_id:<5} {card_uid:<25} {name:<30}")
            else:
                print("No users found.")
            input("\nPress Enter to continue...")
            
        elif choice == "3":
            # View Recent Events
            print("\n--- RECENT EVENTS ---")
            events = get_all_events()
            if events:
                print(f"{'Name':<20} {'Event':<10} {'Timestamp':<25}")
                print("-" * 55)
                for name, event_type, timestamp in events:
                    print(f"{name:<20} {event_type:<10} {timestamp:<25}")
            else:
                print("No events found.")
            input("\nPress Enter to continue...")
            
        elif choice == "4":
            # Start RFID Scanner
            print("\n--- RFID SCANNER ---")
            print("RFID scanner activated. Enter 'scan <CARD_UID>' to simulate a card scan.")
            print("Example: 'scan öö122ö8333'")
            print("Enter 'exit' to return to the main menu.")
            
            rfid_reader.start()
            
            while True:
                scan_input = input("\n> ").strip()
                
                if scan_input.lower() == 'exit':
                    break
                elif scan_input.lower().startswith('scan '):
                    _, card_uid = scan_input.split(' ', 1)
                    card_uid = card_uid.strip()
                    if validate_card_uid(card_uid):
                        rfid_reader.process_scan(card_uid)
                    else:
                        print(f"Invalid card UID format: {card_uid}")
                else:
                    print("Unknown command. Use 'scan <CARD_UID>' or 'exit'")
            
            rfid_reader.stop()
            
        elif choice == "5":
            # Exit
            print("\nExiting application. Goodbye!")
            break
            
        else:
            print("\nInvalid choice. Please try again.")
            input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
