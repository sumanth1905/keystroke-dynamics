import re
import sys
import os
import pickle
import numpy as np
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import keyboard
from sklearn.preprocessing import StandardScaler

# File paths
LOCKSCREEN_FILE = "lockscreen.py"
TRAIN_AUTH_FILE = "train_auth.py"
MODEL_FILE = "typing_model.pkl"

class KeystrokeRecorder:
    def __init__(self, parent, password):
        self.parent = parent
        self.password = password
        self.typed = ""
        self.times = []
        self.last_time = None
        self.recording = False
        
        # Create a dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Record Keystrokes")
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
        
        # Instructions
        tk.Label(self.dialog, text=f"Type the password: {password}", font=('Arial', 12)).pack(pady=20)
        
        # Password display
        self.password_var = tk.StringVar()
        tk.Label(self.dialog, textvariable=self.password_var, font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Status
        self.status_var = tk.StringVar(value="Ready to record...")
        tk.Label(self.dialog, textvariable=self.status_var, font=('Arial', 10)).pack(pady=10)
        
        # Start button
        tk.Button(self.dialog, text="Start Recording", command=self.start_recording).pack(pady=10)
        
        self.result = None

    def start_recording(self):
        self.status_var.set("Recording... Type the password")
        self.recording = True
        self.typed = ""
        self.times = []
        self.last_time = None
        self.password_var.set("")
        
        # Start keyboard hook in a separate thread
        threading.Thread(target=self.record_keys, daemon=True).start()
    
    def record_keys(self):
        keyboard.on_press(self.on_key_press)
        
        # Wait until recording is done
        while self.recording and len(self.typed) < len(self.password):
            time.sleep(0.01)
            
        keyboard.unhook_all()
        
        # Check if password is correct
        if self.typed == self.password:
            self.status_var.set("✅ Recording complete!")
            self.result = self.times
            # Close dialog after a short delay
            self.dialog.after(1000, self.dialog.destroy)
        else:
            self.status_var.set("❌ Incorrect password! Try again.")
            self.password_var.set("")
    
    def on_key_press(self, event):
        if not self.recording:
            return
            
        current_time = time.time()
        
        # Only process regular keys
        if len(event.name) == 1:
            self.typed += event.name
            self.password_var.set("*" * len(self.typed))
            
            if self.last_time is not None:
                self.times.append(current_time - self.last_time)
            
            self.last_time = current_time
            
            # Check if we've completed the password
            if len(self.typed) >= len(self.password):
                self.recording = False

class UpdateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Typing Authentication Settings")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # Set up the main frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Authentication System Settings", font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Update Options", padding=10)
        options_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Buttons
        ttk.Button(options_frame, text="Change Password / Train Model", 
                  command=self.update_password).pack(fill=tk.X, pady=5)
        ttk.Button(options_frame, text="Change Threshold", 
                  command=self.update_threshold).pack(fill=tk.X, pady=5)
        ttk.Button(options_frame, text="Change Security Questions", 
                  command=self.update_security_questions).pack(fill=tk.X, pady=5)
        ttk.Button(options_frame, text="Change Matrix Rain Character", 
                  command=self.update_matrix_character).pack(fill=tk.X, pady=5)
        ttk.Button(options_frame, text="Change Everything", 
                  command=self.update_everything).pack(fill=tk.X, pady=5)
        
        # Status frame
        self.status_frame = ttk.LabelFrame(main_frame, text="Status", padding=10)
        self.status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.status_text = tk.Text(self.status_frame, height=8, wrap=tk.WORD)
        self.status_text.pack(fill=tk.BOTH, expand=True)
        self.status_text.config(state=tk.DISABLED)
        
        # Exit button
        ttk.Button(main_frame, text="Exit", command=root.destroy).pack(pady=10)
    
    def log(self, message):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        
    def get_keystroke_times(self, password):
        recorder = KeystrokeRecorder(self.root, password)
        self.root.wait_window(recorder.dialog)
        return password, recorder.result
        
    def collect_typing_data(self, password, n_attempts=5):
        data = []
        self.log(f"\nPlease type your password '{password}' {n_attempts} times.")
        
        for attempt in range(n_attempts):
            if messagebox.askyesno("Ready?", f"Attempt {attempt + 1} of {n_attempts}: Ready to record typing?"):
                typed, times = self.get_keystroke_times(password)
                
                if not times:
                    self.log("Recording was cancelled or failed.")
                    continue
                    
                if len(times) == len(password) - 1:
                    data.append(times)
                    self.log(f"✅ Attempt {attempt + 1} recorded.")
        
        return np.array(data) if data else np.array([])
        
    def train_model(self):
        # Get current password from train_auth.py
        with open(TRAIN_AUTH_FILE, "r") as file:
            content = file.read()
        match = re.search(r'PASSWORD\s*=\s*"(.+?)"', content)
        if not match:
            self.log("❌ Error: Could not retrieve password from train_auth.py")
            return
        password = match.group(1)

        # Collect user typing data
        train_data = self.collect_typing_data(password, n_attempts=5)
        if len(train_data) == 0:
            self.log("❌ No valid typing data collected. Model training aborted.")
            return

        scaler = StandardScaler()
        scaled_train_data = scaler.fit_transform(train_data)

        model = {
            "train_data": scaled_train_data,
            "scaler": scaler,
            "avg_self_similarity": np.mean(scaled_train_data),
            "min_self_similarity": np.min(scaled_train_data)
        }

        # Remove old model if exists
        if os.path.exists(MODEL_FILE):
            os.remove(MODEL_FILE)

        with open(MODEL_FILE, "wb") as model_file:
            pickle.dump(model, model_file)

        self.log("✅ New model trained and saved successfully!")
    
    def update_password(self):
        choice = messagebox.askyesno("Password Update", "Do you want to change the password?\n(Yes = change password & train model, No = only train model)")
        
        if choice:
            new_password = simpledialog.askstring("New Password", "Enter new password:", parent=self.root)
            if new_password:
                with open(TRAIN_AUTH_FILE, "r") as file:
                    content = file.read()
                content = re.sub(r'PASSWORD\s*=\s*".*?"', f'PASSWORD = "{new_password}"', content)
                with open(TRAIN_AUTH_FILE, "w") as file:
                    file.write(content)
                self.log("✅ Password updated successfully!")
            else:
                self.log("Password change cancelled.")
                return
        
        self.train_model()
        
    def update_threshold(self):
        new_threshold = simpledialog.askstring("Update Threshold", "Enter new threshold (e.g., 0.10):", parent=self.root)
        if new_threshold:
            with open(TRAIN_AUTH_FILE, "r") as file:
                content = file.read()
            content = re.sub(r'THRESHOLD\s*=\s*[\d\.]+', f'THRESHOLD = {new_threshold}', content)
            with open(TRAIN_AUTH_FILE, "w") as file:
                file.write(content)
            self.log("✅ Threshold updated successfully!")
        else:
            self.log("Threshold update cancelled.")
            
    def update_security_questions(self):
        questions_dialog = SecurityQuestionsDialog(self.root)
        self.root.wait_window(questions_dialog.dialog)
        
        if questions_dialog.questions:
            with open(LOCKSCREEN_FILE, "r") as file:
                content = file.read()
            
            new_questions_str = "{\n" + "\n".join(f'    \"{q}\": \"{a}\",' for q, a in questions_dialog.questions.items()) + "\n}"
            content = re.sub(r'self\.security_questions\s*=\s*{.*?}', f'self.security_questions = {new_questions_str}', content, flags=re.DOTALL)

            with open(LOCKSCREEN_FILE, "w") as file:
                file.write(content)
            self.log("✅ Security questions updated successfully!")
        else:
            self.log("Security questions update cancelled.")
    
    def update_matrix_character(self):
        new_character = simpledialog.askstring("Matrix Character", "Enter new Matrix character to unlock security questions:", parent=self.root)
        if new_character:
            with open(LOCKSCREEN_FILE, "r") as file:
                content = file.read()
            content = re.sub(r'if char == [\'\"].*?[\'\"]:', f'if char == \"{new_character}\":', content)
            with open(LOCKSCREEN_FILE, "w") as file:
                file.write(content)
            self.log("✅ Matrix Rain character updated successfully!")
        else:
            self.log("Matrix character update cancelled.")
    
    def update_everything(self):
        if messagebox.askyesno("Update Everything", "This will update all settings. Continue?"):
            self.update_password()
            self.update_threshold()
            self.update_security_questions()
            self.update_matrix_character()
            self.log("🎉 All settings updated successfully!")
        else:
            self.log("Update everything cancelled.")

class SecurityQuestionsDialog:
    def __init__(self, parent):
        self.parent = parent
        self.questions = {}
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Security Questions")
        self.dialog.geometry("500x450")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)  # Handle window close properly
        
        # Center dialog
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
        
        # Instructions
        ttk.Label(self.dialog, text="Security Questions Setup", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        ttk.Label(self.dialog, text="You must set exactly 3 security questions", 
                 font=('Arial', 10)).pack(pady=0)
        
        # Questions frame
        questions_frame = ttk.Frame(self.dialog, padding=10)
        questions_frame.pack(fill=tk.BOTH, expand=True)
        
        # Main content frame
        content_frame = ttk.Frame(questions_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create 3 question frames
        self.question_frames = []
        self.question_vars = []
        self.answer_vars = []
        
        for i in range(3):
            frame = ttk.LabelFrame(content_frame, text=f"Question {i+1}")
            frame.pack(fill=tk.X, pady=5, padx=5)
            
            question_var = tk.StringVar()
            answer_var = tk.StringVar()
            
            ttk.Label(frame, text="Question:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
            question_entry = ttk.Entry(frame, width=40, textvariable=question_var)
            question_entry.grid(row=0, column=1, padx=5, pady=5)
            
            ttk.Label(frame, text="Answer:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
            answer_entry = ttk.Entry(frame, width=40, textvariable=answer_var)
            answer_entry.grid(row=1, column=1, padx=5, pady=5)
            
            self.question_frames.append(frame)
            self.question_vars.append(question_var)
            self.answer_vars.append(answer_var)
        
        # Status label
        self.status_var = tk.StringVar()
        status_label = ttk.Label(self.dialog, textvariable=self.status_var, foreground="red")
        status_label.pack(pady=5)
        
        # Buttons
        buttons_frame = ttk.Frame(self.dialog)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(buttons_frame, text="Save", command=self.save_questions).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT, padx=10)
    
    def save_questions(self):
        # Validate that all questions and answers are filled
        all_filled = True
        empty_fields = []
        
        for i in range(3):
            question = self.question_vars[i].get().strip()
            answer = self.answer_vars[i].get().strip()
            
            if not question:
                empty_fields.append(f"Question {i+1}")
                all_filled = False
            if not answer:
                empty_fields.append(f"Answer {i+1}")
                all_filled = False
        
        if not all_filled:
            self.status_var.set(f"Please fill in all fields: {', '.join(empty_fields)}")
            return
        
        # Check for duplicate questions
        questions = [q.get().strip() for q in self.question_vars]
        if len(set(questions)) != len(questions):
            self.status_var.set("All questions must be unique")
            return
            
        # Save questions and answers
        self.questions = {}
        for i in range(3):
            self.questions[self.question_vars[i].get().strip()] = self.answer_vars[i].get().strip()
            
        # Close dialog
        self.dialog.destroy()
    
    def on_cancel(self):
        # Clear questions and close
        self.questions = {}
        self.dialog.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = UpdateApp(root)
    root.mainloop()