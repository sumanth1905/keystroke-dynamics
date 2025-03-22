import sys
import tkinter as tk
from tkinter import ttk
import time
import numpy as np
from sklearn.preprocessing import StandardScaler
import pickle
from datetime import datetime
import logging
import os
import ctypes
import win32con
import win32gui
import random

# Import password and threshold from train_auth.py
from train_auth import PASSWORD, THRESHOLD

# Lock file path
LOCK_FILE_PATH = "lockscreen.lock"

# Set up logging
logging.basicConfig(
    filename='lockscreen_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

class KeystrokeLockscreen:
    def __init__(self, root):
        self.root = root
        self.root.title("Security Lockscreen")

        # Make it fullscreen and always on top
        self.root.attributes('-fullscreen', True, '-topmost', True)
        self.root.configure(bg='black')
        
        # Hide taskbar
        self.hide_taskbar()
        
        # Disable alt+f4 and other escape methods
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Block Windows keys
        self.block_windows_keys()

        # Create the canvas for the Matrix Rain effect
        self.canvas = tk.Canvas(self.root, width=root.winfo_screenwidth(), height=root.winfo_screenheight(), bg='black', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        # Initialize Matrix Rain effect parameters
        self.matrix_rain_drops = []
        self.matrix_rain_running = True
        self.init_matrix_rain_effect()
        
        # Security questions and answers
        self.security_questions = {
    "gjkkj": "sum",
    "hghjhkj": "suman",
    "jhgbj": "sumanth",
}
        self.current_question_index = 0
        self.security_mode = False
        
        # Create GUI elements
        self.setup_gui()
        
        # Initialize authentication variables
        self.current_input = ""
        self.keystroke_times = []
        self.last_keystroke_time = None
        
        # Load the trained model
        if not self.load_model():
            self.show_error_and_close("Error: No trained model found! Please run training first.")
        
        # Start time update
        self.update_time()

    def hide_taskbar(self):
        """Hide Windows taskbar"""
        hwnd = win32gui.FindWindow("Shell_traywnd", None)
        win32gui.ShowWindow(hwnd, 0)
        self.root.bind('<Key>', lambda e: self.prevent_start_menu(e))
        
    def show_taskbar(self):
        """Show Windows taskbar (called when unlocking)"""
        hwnd = win32gui.FindWindow("Shell_traywnd", None)
        win32gui.ShowWindow(hwnd, 1)
        
    def prevent_start_menu(self, event):
        """Prevent Windows key and Start menu"""
        if event.keycode in [win32con.VK_LWIN, win32con.VK_RWIN]:
            return 'break'
        
    def setup_gui(self):
        """Set up the GUI elements"""
        self.frame = ttk.Frame(self.root)
        self.frame.place(relx=0.5, rely=0.4, anchor='center')
        
        self.password_frame = ttk.Frame(self.frame)
        self.password_frame.pack()
        
        self.instruction_label = ttk.Label(
            self.password_frame,
            text="Type your password and press Enter to unlock",
            font=('Arial', 20)
        )
        self.instruction_label.pack(pady=10)
        
        self.error_label = ttk.Label(
            self.password_frame,
            text="",
            font=('Arial', 20),
            foreground='red'
        )
        self.error_label.pack(pady=5)
        
        self.password_display = ttk.Label(
            self.password_frame,
            text="",
            font=('Arial', 30)
        )
        self.password_display.pack(pady=10)
        
        self.time_label = ttk.Label(
            self.password_frame,
            text="",
            font=('Arial', 30)
        )
        self.time_label.pack(pady=10)
        self.time_label.bind("<Double-Button-1>", lambda e: self.toggle_matrix_rain())

        # Security questions frame (initially hidden)
        style = ttk.Style()
        style.configure("Custom.TButton", font=("Arial", 20))

        self.question_frame = ttk.Frame(self.frame)
        self.back_button = ttk.Button(
            self.question_frame,
            text="Back to Password",
            command=self.show_password_entry,
            style="Custom.TButton"
        )
        self.back_button.pack(pady=20)
        
        self.question_label = ttk.Label(
            self.question_frame,
            text="",
            font=('Arial', 20)
        )
        self.question_label.pack(pady=10)
        
        self.security_error_label = ttk.Label(
            self.question_frame,
            text="",
            font=('Arial', 20),
            foreground='red'
        )
        self.security_error_label.pack(pady=10)
        
        self.answer_entry = ttk.Entry(self.question_frame, font=("Arial", 18))
        self.answer_entry.pack(pady=10)
        self.answer_entry.bind('<Return>', lambda e: self.check_security_answer())
        
        self.submit_button = ttk.Button(
            self.question_frame,
            text="Submit",
            command=self.check_security_answer,
            style="Custom.TButton"
        )
        self.submit_button.pack(pady=20)
        
    def show_security_questions(self):
        """Switch to security questions mode"""
        self.security_mode = True
        self.current_question_index = 0
        self.password_frame.pack_forget()
        self.question_frame.pack()
        self.show_current_question()
        
    def show_password_entry(self):
        """Switch back to password entry mode"""
        self.security_mode = False
        self.question_frame.pack_forget()
        self.password_frame.pack()
        self.reset_input()
        self.error_label.config(text="")
        self.instruction_label.config(text="Type your password and press Enter to unlock")
        
    def show_current_question(self):
        """Display the current security question"""
        question = list(self.security_questions.keys())[self.current_question_index]
        self.question_label.config(text=question)
        self.security_error_label.config(text="")
        self.answer_entry.delete(0, tk.END)
        self.answer_entry.focus()
        
    def check_security_answer(self):
        """Verify the answer to the security question"""
        current_question = list(self.security_questions.keys())[self.current_question_index]
        correct_answer = self.security_questions[current_question]
        user_answer = self.answer_entry.get().lower().strip()
        
        if user_answer == correct_answer:
            self.current_question_index += 1
            if self.current_question_index >= len(self.security_questions):
                self.unlock_system()
            else:
                self.show_current_question()
        else:
            self.security_error_label.config(text="Incorrect answer")
            self.blink_text(self.security_error_label)
            self.answer_entry.delete(0, tk.END)
        
    def block_windows_keys(self):
        """Block Windows key combinations"""
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        
        if user32.RegisterHotKey(None, 1, win32con.MOD_ALT, win32con.VK_TAB):
            self.root.bind_all('<Key>', lambda e: 'break')
        
        self.root.bind('<Alt-Tab>', lambda e: 'break')
        self.root.bind('<Alt-F4>', lambda e: 'break')
        self.root.bind('<Control-Escape>', lambda e: 'break')
        self.root.bind('<Control-Alt-Delete>', lambda e: 'break')
        self.root.bind('<Shift-Escape>', lambda e: 'break')
        self.root.bind('<Key>', self.on_key_press)
        
    def load_model(self):
        """Load the trained keystroke model"""
        try:
            with open("typing_model.pkl", "rb") as model_file:
                self.model = pickle.load(model_file)
            self.PASSWORD = PASSWORD
            self.THRESHOLD = THRESHOLD
            logging.info("Model loaded successfully")
            return True
        except FileNotFoundError:
            logging.error("No trained model found!")
            return False
            
    def show_error_and_close(self, message):
        """Show error message and close on key press"""
        self.error_label.config(text=message)
        self.root.bind('<Key>', lambda e: self.cleanup())
        
    def update_time(self):
        """Update the time display"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)
        
    def reset_input(self):
        """Reset all input-related variables"""
        self.current_input = ""
        self.keystroke_times = []
        self.last_keystroke_time = None
        self.password_display.config(text="")
        
    def blink_text(self, label):
        """Create blinking effect for text"""
        current_text = label.cget("text")
        label.config(text="")
        self.root.after(200, lambda: label.config(text=current_text))
        
    def on_key_press(self, event):
        """Handle key press events"""
        if self.security_mode:
            return

        if event.keysym == 'Return':
            self.verify_input()
            return 'break'
        
        if event.keysym == 'BackSpace':
            if self.current_input:
                self.current_input = self.current_input[:-1]
                self.keystroke_times = self.keystroke_times[:-1] if self.keystroke_times else []
                self.password_display.config(text="*" * len(self.current_input))
            return 'break'
            
        if event.char and event.char.isprintable():
            current_time = time.time()
            
            if self.last_keystroke_time is not None:
                interval = current_time - self.last_keystroke_time
                self.keystroke_times.append(interval)
            
            self.last_keystroke_time = current_time
            self.current_input += event.char
            
            self.password_display.config(text="*" * len(self.current_input))
                
        return 'break'
        
    def verify_input(self):
        """Verify the password and typing pattern"""
        if len(self.current_input) != len(self.PASSWORD) or len(self.keystroke_times) != len(self.PASSWORD) - 1:
            self.handle_failed_attempt("Incorrect password or typing pattern (Score: 0.00) doesn't match!")
            self.reset_input()
            return
            
        if self.current_input != self.PASSWORD:
            self.handle_failed_attempt("Incorrect password or typing pattern (Score: 0.00) doesn't match!")
            self.reset_input()
            return
                
        # Verify typing pattern
        test_features = np.array([self.keystroke_times])
        test_features_scaled = self.model["scaler"].transform(test_features)
        
        # Calculate similarity
        distances = [np.linalg.norm(test_features_scaled - train_sample) 
                    for train_sample in self.model["train_data"]]
        similarity = 1 / (1 + np.mean(distances))
        
        if similarity >= self.THRESHOLD:
            self.unlock_system()
            logging.info("Successful authentication")
        else:
            self.handle_failed_attempt(f"Incorrect password or typing pattern (Score: {similarity:.2f}) doesn't match!")
            self.reset_input()
        
    def handle_failed_attempt(self, message):
        """Handle failed authentication attempts"""
        self.error_label.config(text=message)
        self.blink_text(self.error_label)
        logging.warning(f"Failed authentication attempt: {message}")
        
    def unlock_system(self):
        """Unlock the system and close the lockscreen"""
        self.instruction_label.config(text="Access Granted! Unlocking...")
        logging.info("System unlocked successfully")
        self.show_taskbar()
        self.root.after(1000, self.cleanup)

    def init_matrix_rain_effect(self):
        """Initialize the parameters for the Matrix Rain effect"""
        # Create more drops to cover the entire width of the screen
        for x in range(0, self.root.winfo_screenwidth(), 10):
            for _ in range(10):
                drop = {
                    'x': x,
                    'y': random.randint(-self.root.winfo_screenheight(), 1000),
                    'speed': random.randint(5, 15),
                    'char': random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                }
                self.matrix_rain_drops.append(drop)
        self.update_matrix_rain_effect()

    def update_matrix_rain_effect(self):
        """Update the Matrix Rain effect animation"""
        if not self.matrix_rain_running:
            return

        self.canvas.delete('all')
        for drop in self.matrix_rain_drops:
            # Create text item with tag 'matrix_char'
            self.canvas.create_text(drop['x'], drop['y'], text=drop['char'], fill='lime', font=('Courier', 15), tags='matrix_char')
            drop['y'] += drop['speed']
            if drop['y'] > self.root.winfo_screenheight():
                drop['y'] = random.randint(-self.root.winfo_screenheight(), 0)
                drop['char'] = random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                drop['speed'] = random.randint(5, 15)
        self.root.after(50, self.update_matrix_rain_effect)
    
    def toggle_matrix_rain(self):
        """Toggle the Matrix Rain effect"""
        self.matrix_rain_running = not self.matrix_rain_running
        if self.matrix_rain_running:
            self.update_matrix_rain_effect()
            self.canvas.tag_unbind('matrix_char', '<Double-1>')
        else:
            # Bind double-click event to check for 'character' when paused
            self.canvas.tag_bind('matrix_char', '<Double-1>', self.matrix_double_click_handler)

    def matrix_double_click_handler(self, event):
        """Handle double-clicks on matrix characters"""
        if not self.matrix_rain_running:
            item = self.canvas.find_closest(event.x, event.y)
            char = self.canvas.itemcget(item, 'text')
            if char == "1": # set any one alphanumeric character
                self.show_security_questions()
                self.matrix_rain_running = True
                self.update_matrix_rain_effect()

    def cleanup(self):
        """Cleanup lock file on exit"""
        self.show_taskbar()
        if os.path.exists(LOCK_FILE_PATH):
            os.remove(LOCK_FILE_PATH)
        if self.root.winfo_exists():
            self.root.destroy()

def main():
    # Check if lock file exists
    if os.path.exists(LOCK_FILE_PATH):
        print("Lockscreen is already running.")
        logging.info("Lockscreen is already running.")
        return

    # Create a lock file
    try:
        with open(LOCK_FILE_PATH, 'w') as lock_file:
            lock_file.write(str(os.getpid()))
    except Exception as e:
        print(f"Error creating lock file: {e}")
        logging.error(f"Error creating lock file: {e}")
        return
    
    root = tk.Tk()
    app = KeystrokeLockscreen(root)
    root.protocol("WM_DELETE_WINDOW", app.cleanup)
    root.mainloop()

if __name__ == "__main__":
    main()