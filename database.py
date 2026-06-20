import json
import psycopg2
from paths import SETTINGS_FILE

def _load_settings() -> dict:
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

class Database:
    def __init__(self):
        settings = _load_settings()
        db = settings.get("database", {})
        self._host = db.get("host", "localhost")
        self._dbname = db.get("dbname", "postgres")
        self._user = db.get("user", "postgres")
        self._password = db.get("password", "")
        self._port = db.get("port", 5432)

    def connect(self):
        try:
            return psycopg2.connect(
                host=self._host,
                dbname=self._dbname,
                user=self._user,
                password=self._password,
                port=self._port
            )
        except Exception as e:
            raise ConnectionError(
                f"მონაცემთა ბაზასთან დაკავშირება ვერ მოხერხდა: {e}"
            )