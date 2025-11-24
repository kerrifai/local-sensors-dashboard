# export.py
from __future__ import annotations
from pathlib import Path
import pandas as pd
from database import Database


def export_to_excel(db: Database, output_file: Path) -> None:
    assert db.conn is not None
    query = """
        SELECT timestamp, temperature, humidity, luminosity
        FROM sensor_data
        ORDER BY id ASC
    """
    df = pd.read_sql_query(query, db.conn)
    df.to_excel(output_file, index=False)
