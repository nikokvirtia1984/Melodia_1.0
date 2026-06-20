from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / 'settings.json'
UI_DIR = BASE_DIR / 'ui'
INVOICES_DIR = BASE_DIR / 'invoices'


def ui(name: str) -> str:
    return str(UI_DIR / name)