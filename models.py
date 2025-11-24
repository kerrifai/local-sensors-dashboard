# models.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SensorReading:
    timestamp: datetime
    temperature: float
    humidity: float
    luminosity: float  # en lux, por ejemplo
