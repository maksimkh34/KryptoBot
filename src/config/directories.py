import os
from pathlib import Path


def get_root():
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    return project_root

def get_data():
    os.makedirs(get_root() / "data", exist_ok=True)
    os.chdir(get_root() / "data")
    return os.getcwd()

def get_logs():
    os.makedirs(get_root() / "logs", exist_ok=True)
    os.chdir(get_root() / "logs")
    return os.getcwd()

print(get_data())
