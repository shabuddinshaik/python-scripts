from cx_Freeze import setup, Executable

# Define the base for the executable
base = None
try:
    import tkinter
    base = "Win32GUI"  # Use this for GUI applications on Windows
except ImportError:
    pass

# Define the setup
setup(
    name="URLMonitor",
    version="0.1",
    description="URL Monitoring Application",
    executables=[Executable("monitor_and_ui.py", base=base, targetName="URLMonitor.exe")],
    options={
        'build_exe': {
            'packages': ['requests', 'twilio', 'win32com', 'logging', 'subprocess'],
            'includes': ['tkinter'],
            'include_files': [
                # List any additional files or directories to include here
                ('path/to/your/config/file', 'config/file')
            ],
        }
    }
)
