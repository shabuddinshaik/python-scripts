from cx_Freeze import setup, Executable

base = None

executables = [Executable("monitor_and_ui.py", base=base)]

packages = ["os", "time", "logging", "subprocess", "tkinter", "datetime", "json", "smtplib", "email", "twilio", "threading", "win32com.client"]
options = {
    'build_exe': {    
        'packages': packages,
    },    
}

setup(
    name = "URLMonitor",
    options = options,
    version = "1.0",
    description = 'A URL Monitoring Tool',
    executables = executables
)
