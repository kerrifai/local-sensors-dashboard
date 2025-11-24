# 🖥️ Local Sensor Dashboard (Qt + PySide6)

The **Local Sensor Dashboard** is a desktop application developed in **Python and PySide6 (Qt)** that functions as a lightweight local SCADA/HMI system. It enables real-time acquisition, visualization, storage, and analysis of sensor data sourced from CSV/JSON files.

Designed with a **modular and scalable architecture**, the system simulates industrial data monitoring environments, providing a professional interface for evaluating sensor behavior, alert management, and data-driven decision-making.

---

## 🚀 Key Features

- Modern GUI built with **PySide6 / Qt**, integrating embedded **matplotlib** visualizations
- Data ingestion engine supporting **CSV and JSON** formats with the following fields:
  - `timestamp`
  - `temperature`
  - `humidity`
  - `luminosity`
- Persistent storage using **SQLite** (`sensors.db`) with:
  - `sensor_data`: full historical dataset
  - `alerts`: automatically generated event records
- **SCADA-style monitoring components**, including:
  - Temperature (°C)
  - Relative humidity (%)
  - Luminosity (lux)
  - Sliding window statistics (mean, min, max)
- Intelligent alerting system featuring:
  - Severity levels: `normal`, `warning`, `critical`
  - Configurable thresholds for each parameter
  - Automatic logging into the database
- Historical data export to **Excel (.xlsx)** for reporting and analysis
- **Light/Dark theme switching** directly from the interface
- User configuration persistence via `settings.json` (last loaded file, UI theme, etc.)

---

## 📁 Project Structure

```text
.
├── app.py               # Qt application entry point
├── ui_main_window.py    # Main window, UI, charts and control logic
├── data_acquisition.py  # Data reading and streaming from CSV/JSON
├── database.py          # Data access layer (SQLite)
├── export.py            # Export readings to Excel
├── models.py            # Dataclasses and models (SensorReading, etc.)
├── settings.py          # Configuration manager (settings.json)
├── requirements.txt     # Python dependencies
└── sensors.csv          # Example sensor data file
```



## ▶️ How to Run the Application

### 1. Open VSCode terminal and clone the repository
```bash
git clone https://github.com/your-user/local-sensor-dashboard.git
cd local-sensor-dashboard
```

### 2. Create a virtual environment and activate it.
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```


### 4 .Run the Application
```bash
python app.py
```


## 🧠 How it works the UI

**1. User loads a file (Load CSV/JSON)**

**2. Application streams data with a configurable delay (default 1000ms)**

**3. Dashboard updates:**
  - **Indicators**
  - **Plots**
  - **Statistics** (mean / min / max)

**4. Alerts are logged into SQLite**

**5. User can export complete data to Excel**
