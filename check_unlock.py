import time
import subprocess
import os
import win32api
import win32event
import ctypes
from ctypes import wintypes
import sys

# Constants
EVENT_SYSTEM_DESKTOPSWITCH = 0x0020
execution_delay = 0  # Minimum delay (in seconds) between unlock events

# Global variables
last_execution_time = 0  # Track the last execution time
debounce_time = 10  # Short debounce time in seconds (100ms)

def run_lockscreen():
    """Launch the lockscreen script."""
    global last_execution_time

    # Update the last execution time
    last_execution_time = time.time()

    # Construct the path to lockscreen.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    lockscreen_path = os.path.join(script_dir, "lockscreen.py")

    try:
        print("Launching lockscreen.py...")
        # Launch lockscreen.py without a visible window
        subprocess.Popen(["pythonw", lockscreen_path], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"Error launching lockscreen: {e}")


# Define the callback type using ctypes
WinEventProcType = ctypes.WINFUNCTYPE(
    None,
    ctypes.wintypes.HANDLE,  # hWinEventHook
    ctypes.wintypes.DWORD,   # event
    ctypes.wintypes.HWND,    # hwnd
    ctypes.wintypes.LONG,    # idObject
    ctypes.wintypes.LONG,    # idChild
    ctypes.wintypes.DWORD,   # dwEventThread
    ctypes.wintypes.DWORD    # dwmsEventTime
)


def WinEventProc(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
    """Callback for handling desktop switch events."""
    global last_execution_time

    if event == EVENT_SYSTEM_DESKTOPSWITCH:
        print("Desktop switch event detected.")

        # Get the current time
        current_time = time.time()

        # Check debounce and cooldown
        if current_time - last_execution_time > debounce_time:
            if current_time - last_execution_time > execution_delay:
                print("Triggering lockscreen.py...")
                run_lockscreen()
            else:
                print(f"Event ignored: Cooldown active ({current_time - last_execution_time:.2f}s since last execution).")
        else:
            print("Event ignored: Debounced.")


def main():
    """Main function to set up event hooks and monitor desktop switch events."""
    # Create a mutex to ensure only one instance of the script runs
    mutex_name = "Local\\UnlockMonitor"
    mutex = win32event.CreateMutex(None, 1, mutex_name)

    if win32api.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        print("Another instance is already running.")
        return  # Exit without error

    # Set up event hook for desktop switch (occurs on unlock)
    WinEventProcCallback = WinEventProcType(WinEventProc)
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    hook = user32.SetWinEventHook(
        EVENT_SYSTEM_DESKTOPSWITCH,
        EVENT_SYSTEM_DESKTOPSWITCH,
        0,
        WinEventProcCallback,
        0,
        0,
        0x0002  # WINEVENT_OUTOFCONTEXT
    )

    if not hook:
        print("Failed to set event hook.")
        return

    print("Monitoring for unlock events...")

    try:
        # Message loop to keep the script running
        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    finally:
        # Unhook event and release mutex
        user32.UnhookWinEvent(hook)
        win32api.CloseHandle(mutex)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error in main: {e}")