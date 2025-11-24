# data_acquisition.py
from __future__ import annotations
from pathlib import Path
from typing import Optional, Literal
from datetime import datetime

import pandas as pd

from models import SensorReading


SourceType = Literal["csv", "json"]


class FileDataSource:
    """
    Lee datos desde un CSV o JSON con columnas:
    timestamp, temperature, humidity, luminosity

    Si no hay timestamp, se genera automáticamente en tiempo real.
    """

    def __init__(self, file_path: Path, source_type: SourceType = "csv") -> None:
        self.file_path = file_path
        self.source_type = source_type
        if source_type == "csv":
            self.df = pd.read_csv(file_path)
        else:
            self.df = pd.read_json(file_path)

        self.index = 0

    def next_reading(self) -> Optional[SensorReading]:
        if self.index >= len(self.df):
            return None

        row = self.df.iloc[self.index]
        self.index += 1

        # Timestamp
        if "timestamp" in row and not pd.isna(row["timestamp"]):
            try:
                ts = datetime.fromisoformat(str(row["timestamp"]))
            except Exception:
                ts = datetime.now()
        else:
            ts = datetime.now()

        temp = float(row.get("temperature", 0.0))
        hum = float(row.get("humidity", 0.0))
        lux = float(row.get("luminosity", 0.0))

        return SensorReading(
            timestamp=ts,
            temperature=temp,
            humidity=hum,
            luminosity=lux,
        )
