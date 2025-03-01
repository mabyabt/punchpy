import os
import sqlite3
import datetime
import time
import threading
import tkinter as tk
from tkinter import ttk, font
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
def get_user_by_card(card_uid: str) -> Optional[Tuple[int, str]]:
    """Get user ID and name by card UID."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM users WHERE card_uid = ?", (card_uid,))
    user = cursor.fetchone()
    conn.close()
    return user if user else None

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

class ClockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Clock In/Out System")
        self.root.geometry("800x480")  # Good size for Raspberry Pi display
        self.root.configure(bg="#f0f0f0")
        
        # Set app to fullscreen on Raspberry Pi
        # Uncomment for Raspberry Pi deployment
        # self.root.attributes('-fullscreen', True)
        
        # Create a larger, bold font for the UI
        self.large_font = font.Font(family="Helvetica", size=16, weight="bold")
        self.normal_font = font.Font(family="Helvetica", size=12)
        self.huge_font = font.Font(family="Helvetica", size=24, weight="bold")
        
        # Create main frame
        self.main_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Current time display at the top
        self.time_label = tk.Label(
            self.main_frame, 
            font=self.huge_font, 
            bg="#f0f0f0",
            fg="#333333"
        )
        self.time_label.pack(pady=(0, 20))
        self.update_time()
        
        # Create status frame for scan feedback
        self.status_frame = tk.Frame(self.main_frame, bg="#f0f0f0", height=200)
        self.status_frame.pack(fill=tk.X, pady=20)
        
        # Status label
        self.status_label = tk.Label(
            self.status_frame, 
            text="Please scan your card", 
            font=self.large_font,
            bg="#f0f0f0"
        )
        self.status_label.pack(pady=10)
        
        # Status message (name and clock direction)
        self.message_label = tk.Label(
            self.status_frame, 
            text="", 
            font=self.huge_font,
            bg="#f0f0f0"
        )
        self.message_label.pack(pady=10)
        
        # Create a frame for the input field
        self.input_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
        self.input_frame.pack(fill=tk.X, pady=20)
        
        # Card UID entry field
        self.card_entry = tk.Entry(
            self.input_frame, 
            font=self.normal_font,
            width=30
        )
        self.card_entry.pack(pady=10)
        self.card_entry.focus_set()  # Auto-focus the entry field
        
        # Bind the Enter key to process_card function
        self.card_entry.bind("<Return>", self.process_card)
        
        # Recent activity listbox
        self.activity_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
        self.activity_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.activity_label = tk.Label(
            self.activity_frame, 
            text="Recent Activity", 
            font=self.normal_font,
            bg="#f0f0f0"
        )
        self.activity_label.pack(anchor=tk.W)
        
        self.activity_list = tk.Listbox(
            self.activity_frame,
            font=self.normal_font,
            height=8
        )
        self.activity_list.pack(fill=tk.BOTH, expand=True)
        
        # Create a button to exit the application
        self.exit_button = tk.Button(
            self.main_frame, 
            text="Exit", 
            command=self.root.destroy,
            font=self.normal_font
        )
        self.exit_button.pack(pady=10)
        
        # Status variables
        self.status_timer = None  # For clearing status after delay
        
        # Set up the database
        setup_database()
        
        # For testing - load some recent activity
        self.load_recent_activity()
        
        # Optionally set up keyboard capture for RFID reader
        # This is commented out as we're using the entry field in this demo
        # self.setup_keyboard_capture()
    
    def update_time(self):
        """Update the time display."""
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)  # Update every second
    
    def process_card(self, event=None):
        """Process a card scan from the entry field."""
        card_uid = self.card_entry.get().strip()
        self.card_entry.delete(0, tk.END)  # Clear the entry field
        
        if not card_uid:
            return
        
        # Check if user exists
        user = get_user_by_card(card_uid)
        
        if not user:
            # Unknown card - show red status
            self.show_status(False, f"Unknown Card: {card_uid}")
            return
        
        user_id, name = user
        last_event = get_last_event(user_id)
        
        # Toggle between clock in/out
        event_type = "out" if last_event == "in" else "in"
        
        # Record the event
        if record_clock_event(user_id, event_type):
            # Show green status
            self.show_status(True, f"{name} clocked {event_type}!")
            
            # Add to recent activity
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            self.activity_list.insert(0, f"{current_time} - {name} clocked {event_type}")
            
            # Limit list to 8 items
            if self.activity_list.size() > 8:
                self.activity_list.delete(8)
        else:
            # Show red status for error
            self.show_status(False, "Error recording event")
    
    def show_status(self, success, message):
        """Show status with color indication."""
        # Cancel any pending status reset
        if self.status_timer:
            self.root.after_cancel(self.status_timer)
        
        # Set colors based on success
        if success:
            bg_color = "#4CAF50"  # Green
            fg_color = "white"
        else:
            bg_color = "#F44336"  # Red
            fg_color = "white"
        
        # Update status display
        self.status_frame.configure(bg=bg_color)
        self.status_label.configure(bg=bg_color, fg=fg_color, text="Card Scanned")
        self.message_label.configure(bg=bg_color, fg=fg_color, text=message)
        
        # Schedule reset of status after 3 seconds
        self.status_timer = self.root.after(3000, self.reset_status)
    
    def reset_status(self):
        """Reset the status display."""
        self.status_frame.configure(bg="#f0f0f0")
        self.status_label.configure(bg="#f0f0f0", fg="#333333", text="Please scan your card")
        self.message_label.configure(bg="#f0f0f0", fg="#333333", text="")
        self.status_timer = None
    
    def load_recent_activity(self):
        """Load recent activity from the database."""
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT u.name, c.event_type, c.timestamp 
                FROM clock_events c 
                JOIN users u ON c.user_id = u.id 
                ORDER BY c.timestamp DESC 
                LIMIT 8
                """
            )
            events = cursor.fetchall()
            conn.close()
            
            for name, event_type, timestamp in events:
                time_str = datetime.datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
                self.activity_list.insert(tk.END, f"{time_str} - {name} clocked {event_type}")
        except Exception as e:
            print(f"Error loading recent activity: {e}")
    
    def setup_keyboard_capture(self):
        """
        Set up direct keyboard capture for RFID reader.
        Note: This is an alternative to using the entry field.
        This would require the pynput library.
        """
        pass
        # Uncomment below code if using pynput
        # from pynput import keyboard
        
        # def on_press(key):
        #     try:
        #         # Process key presses here
        #         pass
        #     except Exception as e:
        #         print(f"Error in keyboard handler: {e}")
        
        # # Start keyboard listener
        # keyboard_listener = keyboard.Listener(on_press=on_press)
        # keyboard_listener.start()


if __name__ == "__main__":
    # Create and run the app
    root = tk.Tk()
    app = ClockApp(root)
    root.mainloop()
