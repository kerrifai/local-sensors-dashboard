# settings.py
import json
from pathlib import Path
from typing import Any, Dict

SETTINGS_FILE = Path("settings.json")


class SettingsManager:
    def __init__(self, path: Path = SETTINGS_FILE) -> None:
        self.path = path
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self._data = {}
        else:
            self._data = {}

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=4), encoding="utf-8")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
