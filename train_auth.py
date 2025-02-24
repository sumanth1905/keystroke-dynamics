import time
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import msvcrt
import sys

# Constants
PASSWORD = ""
THRESHOLD = 0.10  # Reduced threshold for more lenient matching
NUM_FEATURES = len(PASSWORD) - 1  # Number of inter-key intervals

def get_keystroke_times():
    """Capture the timing between keystrokes"""
    times = []
    typed = ""
    last_time = None
    
    # Get the first character
    char = msvcrt.getch().decode()
    typed += char
    sys.stdout.write(char)
    last_time = time.time()
    
    # Get remaining characters
    while len(typed) < len(PASSWORD):
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
    data = []
    print(f"Please type your password '{password}' {n_attempts} times:")
    
    for attempt in range(n_attempts):
        input(f"\nAttempt {attempt + 1} of {n_attempts}: Press Enter when ready to start typing.")
        print("Start typing the password...")
        
        typed, times = get_keystroke_times()
        
        if typed != password:
            print("Incorrect password entered. Please try again.")
            continue
            
        if len(times) == NUM_FEATURES:
            data.append(times)
            print(f"Attempt {attempt + 1} recorded.")
            print("Inter-key intervals:", [f"{t:.3f}s" for t in times])
    
    return np.array(data)

def similarity_score(test_features, train_features):
    # Compute average Euclidean distance across all samples
    distances = [np.linalg.norm(test_features - train_sample) for train_sample in train_features]
    avg_distance = np.mean(distances)
    # Convert distance to similarity score
    similarity = 1 / (1 + avg_distance)
    return similarity

def train_model():
    print("Training phase:")
    train_data = collect_typing_data(PASSWORD, n_attempts=5)
    scaler = StandardScaler()
    scaled_train_data = scaler.fit_transform(train_data)
    
    # Calculate self-similarity scores for training data
    self_similarities = []
    for i in range(len(scaled_train_data)):
        test_sample = scaled_train_data[i:i+1]
        remaining_samples = np.delete(scaled_train_data, i, axis=0)
        sim = similarity_score(test_sample, remaining_samples)
        self_similarities.append(sim)
    
    avg_self_similarity = np.mean(self_similarities)
    min_self_similarity = np.min(self_similarities)
    
    model = {
        "train_data": scaled_train_data,
        "scaler": scaler,
        "avg_self_similarity": avg_self_similarity,
        "min_self_similarity": min_self_similarity
    }
    
    with open("typing_model.pkl", "wb") as model_file:
        pickle.dump(model, model_file)
    
    print("\nModel trained and saved successfully!")
    print("\nYour typing pattern statistics:")
    print("Average intervals:", [f"{t:.3f}s" for t in np.mean(train_data, axis=0)])
    print("Standard deviations:", [f"{t:.3f}s" for t in np.std(train_data, axis=0)])
    print(f"Average self-similarity score: {avg_self_similarity:.3f}")
    print(f"Minimum self-similarity score: {min_self_similarity:.3f}")
    return model

def verify_typing(model, scaler, train_data, password):
    print("\nVerification phase:")
    input("Press Enter when ready to start typing your password.")
    print("Start typing...")
    
    typed, times = get_keystroke_times()
    
    if typed != password:
        print("Incorrect password entered. Access Denied!")
        return
        
    if len(times) != NUM_FEATURES:
        print("Invalid typing pattern. Access Denied!")
        return
        
    test_features = np.array([times])
    test_features_scaled = scaler.transform(test_features)
    similarity = similarity_score(test_features_scaled, train_data)
    
    print(f"\nYour typing intervals: {[f'{t:.3f}s' for t in times]}")
    print(f"Similarity score: {similarity:.2f}")
    
    if similarity >= THRESHOLD:
        print("Access Granted!")
    else:
        print("Access Denied!")
        print(f"Required threshold: {THRESHOLD}")
        print("Try typing with a more consistent rhythm.")

if __name__ == "__main__":
    try:
        with open("typing_model.pkl", "rb") as model_file:
            model = pickle.load(model_file)
            print("Model loaded successfully!")
    except FileNotFoundError:
        print("Model not found. Training a new model...")
        model = train_model()
        
    train_data = model["train_data"]
    scaler = model["scaler"]
    verify_typing(model, scaler, train_data, PASSWORD)