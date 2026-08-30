"""
Author: Toby Baker
Title: Interface for capturing metrics about monitors on different OS's
Date Created: 28 Nov 2018
"""

try:
    import win32api, win32con
except ImportError:
    win32api = win32con = None

try:
    import pyautogui
except Exception:
    # pyautogui needs a display; it raises on a headless host rather than
    # simply failing to import, so this catches more than ImportError
    pyautogui = None

class Monitor():
    '''Class for storing data about the display'''
    def __init__(self):
        # Windows only at this stage
        pass

class WindowsMonitor(Monitor):
    def __init__(self):
        super().__init__()
        if win32api is None:
            raise ImportError("WindowsMonitor requires pywin32: pip install pywin32")
        self.width = win32api.GetSystemMetrics(0)
        self.height = win32api.GetSystemMetrics(1)
        print('Monitor Width: %d, Monitor Height: %d' % (self.width, self.height))
        print("[DEBUG] Windows Monitor Initialized")

class LinuxMonitor(Monitor):
    def __init__(self):
        super().__init__()
        if pyautogui is None:
            raise ImportError("LinuxMonitor requires pyautogui and an available display")
        self.width, self.height = pyautogui.size()
        print('Monitor Width: %d, Monitor Height: %d' % (self.width, self.height))
        print("[DEBUG] Linux Monitor Initialized")

class MacMonitor(Monitor):
    '''
    Screen geometry on macOS. pyautogui.size() is already the mechanism
    LinuxMonitor uses and it supports Darwin, so this needs no new dependency
    -- the previous blocker was the unconditional 'import mouse' in this
    module's fallback branch, which has no macOS backend and was never used
    here in the first place.
    '''
    def __init__(self):
        super().__init__()
        if pyautogui is None:
            raise ImportError("MacMonitor requires pyautogui and an available display")
        self.width, self.height = pyautogui.size()
        print('Monitor Width: %d, Monitor Height: %d' % (self.width, self.height))
        print("[DEBUG] Mac Monitor Initialized")