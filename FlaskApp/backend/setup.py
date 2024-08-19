from cx_Freeze import setup, Executable

setup(
    name = "monitoring_app",
    version = "1.0",
    description = "Endpoint Monitoring and Alerting Application",
    executables = [Executable("app.py")]
)
