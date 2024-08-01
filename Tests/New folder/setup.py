from cx_Freeze import setup, Executable

# GUI applications require a different base on Windows (the default is for a console application).
base = None

executables = [
    Executable("monitor_urls.py", base=base),
    Executable("ui.py", base=base)
]

setup(
    name="URLMonitor",
    version="1.0",
    description="URL Monitoring with GUI Configuration",
    executables=executables,
    options={
        "build_exe": {
            "packages": ["tkinter", "twilio"],  # Add any additional packages your scripts require
            "include_files": [],  # List any additional files or data to include in the build
        }
    }
)
