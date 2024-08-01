import sys
from cx_Freeze import setup, Executable

build_exe_options = {
    "includes": ["tkinter", "win32com.client"],
    "packages": ["twilio", "logging", "subprocess", "time", "socket", "json", "threading"],
    "include_files": []  # Add any additional files needed (e.g., config files)
}

base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="URLMonitor",
    version="2.0",
    description="URL Monitoring Application with GUI",
    options={"build_exe": build_exe_options},
    executables=[Executable("monitor_and_ui.py", base=base, target_name="URLMonitor.exe")]
)
