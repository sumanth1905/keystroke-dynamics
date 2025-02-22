import time
import requests
import os

BLYNK_AUTH = "v9Ii7AZN7tIMLLHdVjZCNaosGbUk99Eb"
BLYNK_URL = "https://blynk.cloud/external/api/update"
LOG_FILE = "lockscreen_log.txt"

last_handled_log = ""
failed_attempts = 0

def read_last_log_entry():
    try:
        # Wait until file exists before reading
        while not os.path.exists(LOG_FILE):
            time.sleep(0.5)
            
        with open(LOG_FILE, "r") as file:
            lines = file.readlines()
            if lines:
                return lines[-1].strip()
    except Exception as e:
        print(f"⚠️ Error reading log file: {e}")
    return ""

def send_blynk_update(pin, value):
    try:
        requests.get(f"{BLYNK_URL}?token={BLYNK_AUTH}&{pin}={value}", timeout=5)
    except Exception as e:
        print(f"⚠️ Blynk error: {e}")

def reset_leds_after_success():
    print("✅ System unlocked! Turning off Red LED & Blinking Green LED once...")
    send_blynk_update("V1", 0)
    send_blynk_update("V3", 0)
    send_blynk_update("V2", 1)
    time.sleep(2)
    send_blynk_update("V2", 0)
    print("✅ Green LED blinked once successfully!")

def reset_after_success():
    global failed_attempts
    failed_attempts = 0
    reset_leds_after_success()

def monitor_log():
    global last_handled_log, failed_attempts
    print(f"🔍 Monitoring {LOG_FILE}...")

    # Wait for log file to exist before opening
    while not os.path.exists(LOG_FILE):
        print("⌛ Waiting for log file to be created...")
        time.sleep(1)

    with open(LOG_FILE, "r") as file:
        file.seek(0, 2)

        while True:
            line = file.readline()
            if not line:
                time.sleep(0.5)
                
                # Handle empty file scenario
                try:
                    if os.stat(LOG_FILE).st_size == 0:
                        continue
                except FileNotFoundError:
                    continue

                last_entry = read_last_log_entry()
                if last_entry and "System unlocked successfully" in last_entry and last_entry != last_handled_log:
                    reset_after_success()
                    last_handled_log = last_entry
                continue

            print(f"📜 Log: {line.strip()}")

            if "Failed authentication attempt" in line:
                failed_attempts += 1

                if failed_attempts >= 3:
                    send_blynk_update("V1", 1)
                if failed_attempts >= 5:
                    send_blynk_update("V3", 1)
                    time.sleep(1)
                    send_blynk_update("V3", 0)

            elif "Successful authentication" in line:
                print("🎉 Success detected in log!")
                reset_after_success()
                last_handled_log = line.strip()

if __name__ == "__main__":
    monitor_log()