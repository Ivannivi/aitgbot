import os
import sys


def get_base_path() -> str:
    """Get the base path for the application (works for both dev and compiled)"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.dirname(sys.executable)
    else:
        # Running in development
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_data_path(filename: str) -> str:
    """Get path for data files (.env, .db) - next to executable or project root"""
    return os.path.join(get_base_path(), filename)


def get_resource_path(relative_path: str) -> str:
    """Get path for bundled resources (templates) - inside executable or src folder"""
    if getattr(sys, 'frozen', False):
        # Running as compiled - resources are in temp dir
        base = sys._MEIPASS
    else:
        # Running in development - resources are in src folder
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)
