import re
import sys
import os
import pickle
import numpy as np
import time
import msvcrt
from sklearn.preprocessing import StandardScaler

# File paths
LOCKSCREEN_FILE = "lockscreen.py"
TRAIN_AUTH_FILE = "train_auth.py"
MODEL_FILE = "typing_model.pkl"

def get_keystroke_times(password):
    """Capture keystroke timings from user input."""
    times = []
    typed = ""
    last_time = None
    
    print("\nStart typing the password...")

    # Get first character
    char = msvcrt.getch().decode()
    typed += char
    sys.stdout.write(char)
    last_time = time.time()

    # Get remaining characters
    while len(typed) < len(password):
        char = msvcrt.getch().decode()
        current_time = time.time()
        if last_time is not None:
            times.append(current_time - last_time)
        last_time = current_time
        typed += char
        sys.stdout.write(char)

    print()  # New line after password
    return typed, times

def collect_typing_data(password, n_attempts=5):
    """Collect typing data from user."""
    data = []
    print(f"\nPlease type your password '{password}' {n_attempts} times:")

    for attempt in range(n_attempts):
        input(f"\nAttempt {attempt + 1} of {n_attempts}: Press Enter when ready to start typing.")
        typed, times = get_keystroke_times(password)
        
        if typed != password:
            print("Incorrect password entered. Please try again.")
            continue
            
        if len(times) == len(password) - 1:
            data.append(times)
            print(f"✅ Attempt {attempt + 1} recorded.")

    return np.array(data)

def train_model():
    """Train a new typing model with user input."""
    # Get current password from train_auth.py
    with open(TRAIN_AUTH_FILE, "r") as file:
        content = file.read()
    match = re.search(r'PASSWORD\s*=\s*"(.+?)"', content)
    if not match:
        print("❌ Error: Could not retrieve password from train_auth.py")
        return
    password = match.group(1)

    # Collect user typing data
    train_data = collect_typing_data(password, n_attempts=5)
    if len(train_data) == 0:
        print("❌ No valid typing data collected. Model training aborted.")
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

    print("✅ New model trained and saved successfully!\n")

def update_password():
    """Menu for changing password or training model"""
    print("\n1. set password & train model")
    print("2. Only train the model")
    choice = input("Enter your choice (1 or 2): ").strip()

    if choice == "1":
        change_password()
        train_model()
    elif choice == "2":
        train_model()
    else:
        print("❌ Invalid choice! Returning to main menu.")

def change_password():
    """Update the password in train_auth.py"""
    new_password = input("Enter new password: ").strip()
    with open(TRAIN_AUTH_FILE, "r") as file:
        content = file.read()
    content = re.sub(r'PASSWORD\s*=\s*".*?"', f'PASSWORD = "{new_password}"', content)
    with open(TRAIN_AUTH_FILE, "w") as file:
        file.write(content)
    print("✅ Password updated successfully!\n")

def update_threshold():
    """Update the threshold in train_auth.py"""
    new_threshold = input("Enter new threshold (e.g., 0.10): ").strip()
    with open(TRAIN_AUTH_FILE, "r") as file:
        content = file.read()
    content = re.sub(r'THRESHOLD\s*=\s*[\d\.]+', f'THRESHOLD = {new_threshold}', content)
    with open(TRAIN_AUTH_FILE, "w") as file:
        file.write(content)
    print("✅ Threshold updated successfully!\n")

def update_security_questions():
    """Update security questions in lockscreen.py"""
    print("\nEnter security questions and answers (leave blank to finish):")
    new_security_questions = {}
    while True:
        question = input("Question: ").strip()
        if not question:
            break
        answer = input("Answer: ").strip()
        new_security_questions[question] = answer

    with open(LOCKSCREEN_FILE, "r") as file:
        content = file.read()
    
    new_questions_str = "{\n" + "\n".join(f'    \"{q}\": \"{a}\",' for q, a in new_security_questions.items()) + "\n}"
    content = re.sub(r'self\.security_questions\s*=\s*{.*?}', f'self.security_questions = {new_questions_str}', content, flags=re.DOTALL)

    with open(LOCKSCREEN_FILE, "w") as file:
        file.write(content)
    print("✅ Security questions updated successfully!\n")

def update_matrix_character():
    """Update the Matrix Rain character in lockscreen.py"""
    new_character = input("Enter new Matrix character to unlock security questions: ").strip()
    with open(LOCKSCREEN_FILE, "r") as file:
        content = file.read()
    content = re.sub(r'if char == [\'\"].*?[\'\"]:', f'if char == \"{new_character}\":', content)
    with open(LOCKSCREEN_FILE, "w") as file:
        file.write(content)
    print("✅ Matrix Rain character updated successfully!\n")

def update_everything():
    """Update all settings at once"""
    update_password()
    update_threshold()
    update_security_questions()
    update_matrix_character()
    print("🎉 All settings updated successfully!\n")

def main():
    """Menu-based system to choose what to update"""
    while True:
        print("\n=== Update Menu ===")
        print("1. Change Password / Train Model")
        print("2. Change Threshold")
        print("3. Change Security Questions")
        print("4. Change Matrix Rain Character")
        print("5. Change Everything")
        print("6. Exit")
        
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == "1":
            update_password()
        elif choice == "2":
            update_threshold()
        elif choice == "3":
            update_security_questions()
        elif choice == "4":
            update_matrix_character()
        elif choice == "5":
            update_everything()
        elif choice == "6":
            print("Exiting... ✅")
            break
        else:
            print("❌ Invalid choice! Please enter a number between 1-6.")

if __name__ == "__main__":
    main()
