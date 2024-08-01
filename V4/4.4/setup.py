import sys
from cx_Freeze import setup, Executable

# Base options for Windows GUI applications
base = "Win32GUI" if sys.platform == "win32" else None

# Define the main application executable
executables = [Executable("monitoring_and_ui.py", base=base)]

# Additional packages required by the application
packages = [
    "os", "sys", "time", "logging", "subprocess", "tkinter", 
    "datetime", "json", "twilio", "threading", "win32com.client", "re"
]

# Define build options
options = {
    'build_exe': {
        'packages': packages,
        'includes': ['win32com.client'],
        'include_files': []  # Add any additional files if necessary
    },
}

# Setup the cx_Freeze build
setup(
    name="URLMonitor",
    version="4.4",
    description='A URL Monitoring Tool with Twilio Integration',
    options=options,
    executables=executables
)
