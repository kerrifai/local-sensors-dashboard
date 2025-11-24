# database.py
import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from models import SensorReading

DB_FILE = Path("sensors.db")


class Database:
    def __init__(self, db_path: Path = DB_FILE) -> None:
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        first_time = not self.db_path.exists()
        self.conn = sqlite3.connect(self.db_path)
        if first_time:
            self._create_tables()

    def _create_tables(self) -> None:
        assert self.conn is not None
        cur = self.conn.cursor()

        # Tabla de datos de sensores
        cur.execute(
            """
            CREATE TABLE sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                luminosity REAL NOT NULL
            );
            """
        )

        # Tabla de alertas
        cur.execute(
            """
            CREATE TABLE alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,       -- 'normal', 'warning', 'critical'
                message TEXT NOT NULL,
                temperature REAL,
                humidity REAL,
                luminosity REAL
            );
            """
        )

        self.conn.commit()

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    # ==================== LECTURAS DE SENSORES ====================

    def insert_reading(self, reading: SensorReading) -> None:
        assert self.conn is not None
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO sensor_data (timestamp, temperature, humidity, luminosity)
            VALUES (?, ?, ?, ?)
            """,
            (
                reading.timestamp.isoformat(),
                reading.temperature,
                reading.humidity,
                reading.luminosity,
            ),
        )
        self.conn.commit()

    def get_last_n_readings(self, n: int = 100) -> List[SensorReading]:
        assert self.conn is not None
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT timestamp, temperature, humidity, luminosity
            FROM sensor_data
            ORDER BY id DESC
            LIMIT ?
            """,
            (n,),
        )
        rows = cur.fetchall()
        readings: List[SensorReading] = []
        for ts_str, temp, hum, lux in reversed(rows):
            readings.append(
                SensorReading(
                    timestamp=datetime.fromisoformat(ts_str),
                    temperature=temp,
                    humidity=hum,
                    luminosity=lux,
                )
            )
        return readings

    # ==================== ALERTAS ====================

    def insert_alert(
        self,
        level: str,
        message: str,
        reading: Optional[SensorReading] = None,
    ) -> None:
        """
        Guarda una alerta en la tabla alerts.
        level: 'normal', 'warning', 'critical'
        message: texto descriptivo
        reading: lectura asociada (opcional)
        """
        assert self.conn is not None
        cur = self.conn.cursor()

        if reading is not None:
            ts = reading.timestamp.isoformat()
            t = reading.temperature
            h = reading.humidity
            l = reading.luminosity
        else:
            ts = datetime.now().isoformat()
            t = h = l = None

        cur.execute(
            """
            INSERT INTO alerts (timestamp, level, message, temperature, humidity, luminosity)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ts, level, message, t, h, l),
        )
        self.conn.commit()

    def get_last_alerts(self, n: int = 50) -> List[tuple]:
        """
        Devuelve las últimas n alertas como tuplas:
        (timestamp, level, message, temperature, humidity, luminosity)
        """
        assert self.conn is not None
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT timestamp, level, message, temperature, humidity, luminosity
            FROM alerts
            ORDER BY id DESC
            LIMIT ?
            """,
            (n,),
        )
        return cur.fetchall()
