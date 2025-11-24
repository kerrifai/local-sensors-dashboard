# app.py
# app.py
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication

from database import Database
from settings import SettingsManager
from ui_main_window import MainWindow

def main() -> None:
    app = QApplication(sys.argv)

    db = Database()
    db.connect()

    settings = SettingsManager()

    window = MainWindow(db=db, settings=settings)
    window.resize(1000, 700)
    window.show()

    exit_code = app.exec()

    settings.save()
    db.close()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
