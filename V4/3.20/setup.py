import sys
from cx_Freeze import setup, Executable

base = "Win32GUI" if sys.platform == "win32" else None

executables = [Executable("monitor_and_ui.py", base=base)]

packages = [
    "os", "sys", "time", "logging", "subprocess", "tkinter", 
    "datetime", "json", "twilio", "threading", "win32com.client"
]

options = {
    'build_exe': {
        'packages': packages,
    },
}

setup(
    name="URLMonitor",
    options=options,
    version="3.20",
    description='A URL Monitoring Tool',
    executables=executables
)
