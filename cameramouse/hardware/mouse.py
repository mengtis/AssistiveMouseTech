"""
Author: Toby Baker
Title: Mouse interface to abstract different mouse APIs
Date Created: 28 Nov 2018
"""

try:
    import win32api, win32con
except ImportError:
    win32api = win32con = None

try:
    # the 'mouse' package ships Windows and Linux backends only; on macOS it
    # raises OSError("Unsupported platform 'Darwin'") at import time
    import mouse
except (ImportError, OSError):
    mouse = None

try:
    import pyautogui
except Exception:
    # pyautogui needs a display; it raises on a headless host rather than
    # simply failing to import, so this catches more than ImportError
    pyautogui = None

class Mouse():
    '''Class for each mouse e.g. Winsdows/Linux/MacOS'''
    def __init__(self):
        self.state = "UP"
        pass

    def left_click(self):
        pass

    def right_click(self):
        pass

    def double_click(self):
        pass

    def move(self, x, y):
        pass

    def moveD(self, dx, dy):
        pass

    def position(self):
        return 0, 0


class WindowsMouse(Mouse):
    def __init__(self):
        super().__init__()
        if win32api is None:
            raise ImportError("WindowsMouse requires pywin32: pip install pywin32")
        print("[DEBUG] Windows Mouse Initialized")

    def left_click(self):
        self.mouse_down()
        self.mouse_up()

    def right_click(self):
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN,0,0,0,0)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP,0,0,0,0)

    def double_click(self):
        self.mouse_down()
        self.mouse_up()
        self.mouse_down()
        self.mouse_up()

    def mouse_down(self):
        # x, y = win32api.GetCursorPos()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0,0,0)
        self.state = "DOWN"

    def mouse_up(self):
        # x, y = win32api.GetCursorPos()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0,0,0)
        self.state = "UP"

    def moveD(self, dx, dy): # MOVE DRAG
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE,int(dx),int(dy),0,0)

    def move(self, x, y):
        win32api.SetCursorPos((int(x), int(y)))

    def position(self):
        return win32api.GetCursorPos()

class LinuxMouse(Mouse):
    def __init__(self):
        super().__init__()
        if mouse is None:
            raise ImportError(
                "LinuxMouse requires the 'mouse' package, which has no macOS "
                "backend. On macOS select os: mac in config.yaml to use MacMouse."
            )
        print("[DEBUG] Linux Mouse Initialized")


    def left_click(self):
        self.mouse_down()
        self.mouse_up()

    def right_click(self):
        mouse.press(button='right')
        mouse.release(button='right')

    def double_click(self):
        self.mouse_down()
        self.mouse_up()
        self.mouse_down()
        self.mouse_up()

    def mouse_down(self):
        mouse.press(button='left')
        # the state machine in control/mouse_states.py releases a held button
        # by checking this flag on entry to InRange and OutOfRange; without the
        # update the button stayed physically down after every drag
        self.state = "DOWN"

    def mouse_up(self):
        mouse.release(button='left')
        self.state = "UP"

    def moveD(self, dx, dy): # MOVE DRAG
        mouse.move(dx, dy, absolute=False, duration=0)

    def move(self, x, y):
        mouse.move(x, y, absolute=True, duration=0)

    def position(self):
        return mouse.get_position()

class MacMouse(Mouse):
    '''
    Cursor actuation on macOS via pyautogui, which supports Darwin where the
    'mouse' package used by LinuxMouse does not.

    NOTE: pyautogui.FAILSAFE is left at its default of True, so slamming the
    cursor into a screen corner raises FailSafeException and stops the program.
    That is a deliberate safety valve rather than an oversight -- disabling it
    for an assistive pointer is a judgement call for the maintainer, not a
    default worth changing silently.

    macOS additionally requires the terminal running this to hold Accessibility
    and Input Monitoring permission under System Settings > Privacy & Security,
    or the cursor calls are silently ignored by the OS.
    '''
    def __init__(self):
        super().__init__()
        if pyautogui is None:
            raise ImportError("MacMouse requires pyautogui and an available display")
        print("[DEBUG] Mac Mouse Initialized")

    def left_click(self):
        self.mouse_down()
        self.mouse_up()

    def right_click(self):
        pyautogui.mouseDown(button='right')
        pyautogui.mouseUp(button='right')

    def double_click(self):
        self.mouse_down()
        self.mouse_up()
        self.mouse_down()
        self.mouse_up()

    def mouse_down(self):
        pyautogui.mouseDown(button='left')
        self.state = "DOWN"

    def mouse_up(self):
        pyautogui.mouseUp(button='left')
        self.state = "UP"

    def moveD(self, dx, dy): # MOVE DRAG
        pyautogui.moveRel(int(dx), int(dy), duration=0)

    def move(self, x, y):
        pyautogui.moveTo(int(x), int(y), duration=0)

    def position(self):
        # pyautogui returns a Point namedtuple, which unpacks as (x, y) exactly
        # like the tuple the other backends return
        return pyautogui.position()

