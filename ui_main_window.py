# ui_main_window.py
from __future__ import annotations

from pathlib import Path
from typing import Optional, List
import statistics as stats

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QLabel,
    QCheckBox,
    QStatusBar,
    QSpinBox,
    QFrame,
    QSizePolicy,
    QProgressBar,
)
from PySide6.QtCore import QTimer, Qt

from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT,
)
from matplotlib.figure import Figure

from database import Database
from data_acquisition import FileDataSource
from models import SensorReading
from export import export_to_excel
from settings import SettingsManager


class MainWindow(QMainWindow):
    def __init__(self, db: Database, settings: SettingsManager, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.settings = settings

        self.setWindowTitle("Dashboard Local de Sensores")

        # ====== PARÁMETROS DE VENTANA Y ALERTAS ======
        # ventana deslizante para estadísticas y gráficos
        self.stats_window = 200

        # UMBRALES DE ALERTA (puedes tunearlos aquí)
        self.ALERT_TEMP_HIGH = 30.0      # ºC
        self.ALERT_TEMP_CRITICAL = 35.0  # ºC
        self.ALERT_HUM_LOW = 30.0        # %
        self.ALERT_HUM_CRITICAL = 20.0   # %
        self.ALERT_LUX_HIGH = 800.0      # lux
        self.ALERT_LUX_CRITICAL = 1000.0 # lux

        # Fuente de datos y lecturas
        self.data_source: Optional[FileDataSource] = None
        self.readings: List[SensorReading] = []

        # Timer de actualización (ms)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._update_data)

        # ===================== LAYOUT PRINCIPAL =====================
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(8)

        # --------- BARRA SUPERIOR: ACCIONES RÁPIDAS ----------
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        self.btn_load = QPushButton("📂 Cargar CSV/JSON")
        self.btn_start = QPushButton("▶ Iniciar")
        self.btn_stop = QPushButton("⏸ Detener")
        self.btn_export = QPushButton("📤 Exportar a Excel")
        self.dark_mode_check = QCheckBox("🌙 Modo oscuro")

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(False)

        self.btn_load.clicked.connect(self.load_file)
        self.btn_start.clicked.connect(self.start_stream)
        self.btn_stop.clicked.connect(self.stop_stream)
        self.btn_export.clicked.connect(self.export_excel)
        self.dark_mode_check.stateChanged.connect(self.toggle_dark_mode)

        for btn in (self.btn_load, self.btn_start, self.btn_stop, self.btn_export):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(30)

        # Tema inicial
        if self.settings.get("dark_mode", False):
            self.dark_mode_check.setChecked(True)
            self._apply_dark_palette()
        else:
            self._apply_light_palette()

        top_layout.addWidget(self.btn_load)
        top_layout.addWidget(self.btn_start)
        top_layout.addWidget(self.btn_stop)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_export)
        top_layout.addWidget(self.dark_mode_check)
        main_layout.addLayout(top_layout)

        # --------- SEGUNDA BARRA: CONTROL DE TIEMPO / RESET ----------
        second_bar = QHBoxLayout()
        second_bar.setSpacing(10)

        lbl_speed = QLabel("Intervalo (ms):")
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(200, 10000)
        self.spin_interval.setSingleStep(200)

        # valor inicial (1000 ms)
        self.spin_interval.setValue(self.timer.interval())

        # 👇 muy importante: ancho mínimo y alineación
        self.spin_interval.setMinimumWidth(80)
        self.spin_interval.setAlignment(Qt.AlignRight)

        self.spin_interval.valueChanged.connect(self._change_interval)

        self.btn_reset = QPushButton("🔄 Reset gráficas")
        self.btn_reset.clicked.connect(self._reset_plots)

        second_bar.addWidget(lbl_speed)
        second_bar.addWidget(self.spin_interval)
        second_bar.addSpacing(20)
        second_bar.addWidget(self.btn_reset)
        second_bar.addStretch()
        main_layout.addLayout(second_bar)

        # --------- PANEL DE INDICADORES SCADA + STATS ----------
        indicators_frame = QFrame()
        indicators_frame.setFrameShape(QFrame.StyledPanel)
        indicators_frame.setObjectName("indicatorsFrame")
        indicators_layout = QHBoxLayout(indicators_frame)
        indicators_layout.setContentsMargins(10, 6, 10, 6)
        indicators_layout.setSpacing(20)

        # --- Temperatura ---
        temp_box = QVBoxLayout()
        temp_title = QLabel("Temperatura")
        temp_title.setAlignment(Qt.AlignCenter)
        temp_title.setStyleSheet("font-size: 14px; font-weight: 600;")

        self.temp_gauge = QProgressBar()
        self.temp_gauge.setRange(0, 50)  # 0–50 ºC
        self.temp_gauge.setFormat("%v °C")
        self.temp_gauge.setTextVisible(True)

        self.lbl_temp_stats = QLabel("μ: —   min: —   max: —")
        self.lbl_temp_stats.setAlignment(Qt.AlignCenter)

        temp_box.addWidget(temp_title)
        temp_box.addWidget(self.temp_gauge)
        temp_box.addWidget(self.lbl_temp_stats)

        # --- Humedad ---
        hum_box = QVBoxLayout()
        hum_title = QLabel("Humedad")
        hum_title.setAlignment(Qt.AlignCenter)
        hum_title.setStyleSheet("font-size: 14px; font-weight: 600;")

        self.hum_gauge = QProgressBar()
        self.hum_gauge.setRange(0, 100)  # 0–100%
        self.hum_gauge.setFormat("%v %")
        self.hum_gauge.setTextVisible(True)

        self.lbl_hum_stats = QLabel("μ: —   min: —   max: —")
        self.lbl_hum_stats.setAlignment(Qt.AlignCenter)

        hum_box.addWidget(hum_title)
        hum_box.addWidget(self.hum_gauge)
        hum_box.addWidget(self.lbl_hum_stats)

        # --- Lux ---
        lux_box = QVBoxLayout()
        lux_title = QLabel("Luminosidad")
        lux_title.setAlignment(Qt.AlignCenter)
        lux_title.setStyleSheet("font-size: 14px; font-weight: 600;")

        self.lux_gauge = QProgressBar()
        self.lux_gauge.setRange(0, 1500)  # 0–1500 lux (ejemplo)
        self.lux_gauge.setFormat("%v lux")
        self.lux_gauge.setTextVisible(True)

        self.lbl_lux_stats = QLabel("μ: —   min: —   max: —")
        self.lbl_lux_stats.setAlignment(Qt.AlignCenter)

        lux_box.addWidget(lux_title)
        lux_box.addWidget(self.lux_gauge)
        lux_box.addWidget(self.lbl_lux_stats)

        indicators_layout.addLayout(temp_box)
        indicators_layout.addLayout(hum_box)
        indicators_layout.addLayout(lux_box)

        main_layout.addWidget(indicators_frame)

        # --------- PANEL DE ALERTA GLOBAL ----------
        alert_frame = QFrame()
        alert_frame.setObjectName("alertFrame")
        alert_layout = QHBoxLayout(alert_frame)
        alert_layout.setContentsMargins(10, 4, 10, 4)

        self.alert_label = QLabel("Estado del sistema: NORMAL")
        self.alert_label.setAlignment(Qt.AlignCenter)
        self.alert_label.setObjectName("alertLabel")

        alert_layout.addWidget(self.alert_label)
        main_layout.addWidget(alert_frame)

        # --------- FIGURA MATPLOTLIB + TOOLBAR ----------
        self.figure = Figure(figsize=(7, 5))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        self.ax_temp = self.figure.add_subplot(3, 1, 1)
        self.ax_hum = self.figure.add_subplot(3, 1, 2)
        self.ax_lux = self.figure.add_subplot(3, 1, 3)
        self.figure.tight_layout()

        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)

        # --------- LABEL INFERIOR ----------
        self.info_label = QLabel("Sin datos cargados.")
        self.info_label.setStyleSheet("color: gray;")
        main_layout.addWidget(self.info_label)

        # --------- STATUS BAR ----------
        status = QStatusBar()
        self.setStatusBar(status)

        # Cargar último fichero si existe
        last_file = self.settings.get("last_file")
        if last_file and Path(last_file).exists():
            p = Path(last_file)
            source_type = "csv" if p.suffix.lower() == ".csv" else "json"
            self._set_data_source(p, source_type)

        # Aplicar tema claro por defecto (se sobreescribe si dark_mode=True)
        if not self.settings.get("dark_mode", False):
            self._apply_light_palette()

    # ===================== FICHERO DE ENTRADA =====================
    def load_file(self) -> None:
        file_path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Selecciona fichero de sensores",
            "",
            "Datos (*.csv *.json);;Todos los archivos (*)",
        )
        if not file_path_str:
            return

        path = Path(file_path_str)
        suffix = path.suffix.lower()
        if suffix == ".csv":
            source_type = "csv"
        elif suffix == ".json":
            source_type = "json"
        else:
            QMessageBox.warning(self, "Error", "Formato no soportado (usa CSV o JSON).")
            return

        self._set_data_source(path, source_type)

    def _set_data_source(self, path: Path, source_type: str = "csv") -> None:
        try:
            self.data_source = FileDataSource(path, source_type=source_type)  # type: ignore[arg-type]
            self.readings.clear()
            self._clear_axes()
            self._reset_indicators()
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.info_label.setText(f"Fuente de datos: {path.name}")
            self.settings.set("last_file", str(path))
            self.statusBar().showMessage("Fichero cargado correctamente.", 3000)
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"No se pudo cargar el fichero:\n{e}"
            )

    # ===================== CONTROL STREAM =====================
    def start_stream(self) -> None:
        if not self.data_source:
            QMessageBox.information(
                self, "Información", "Primero carga un fichero de datos."
            )
            return
        self.timer.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.statusBar().showMessage("Lectura iniciada.", 2000)

    def stop_stream(self) -> None:
        self.timer.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.statusBar().showMessage("Lectura detenida.", 2000)

    def _change_interval(self, value: int) -> None:
        self.timer.setInterval(value)
        self.statusBar().showMessage(f"Intervalo de actualización: {value} ms", 2000)

    def _update_data(self) -> None:
        if not self.data_source:
            return

        reading = self.data_source.next_reading()
        if reading is None:
            self.stop_stream()
            self.statusBar().showMessage("Fin de datos.", 4000)
            return

        self.readings.append(reading)
        self.db.insert_reading(reading)

        self._update_indicators_and_stats()
        self._update_alerts()
        self._update_plots()

        self.info_label.setText(
            f"Última lectura: T={reading.temperature:.1f}°C  "
            f"H={reading.humidity:.1f}%  "
            f"L={reading.luminosity:.1f} lux"
        )

    # ===================== INDICADORES + STATS =====================
    def _reset_indicators(self) -> None:
        self.temp_gauge.setValue(0)
        self.hum_gauge.setValue(0)
        self.lux_gauge.setValue(0)

        self.lbl_temp_stats.setText("μ: —   min: —   max: —")
        self.lbl_hum_stats.setText("μ: —   min: —   max: —")
        self.lbl_lux_stats.setText("μ: —   min: —   max: —")

        self.alert_label.setText("Estado del sistema: NORMAL")
        self._set_alert_style("normal")

    def _update_indicators_and_stats(self) -> None:
        if not self.readings:
            return

        window = self.readings[-self.stats_window :]

        temps = [r.temperature for r in window]
        hums = [r.humidity for r in window]
        luxs = [r.luminosity for r in window]

        # Últimos valores
        t_last = temps[-1]
        h_last = hums[-1]
        l_last = luxs[-1]

        # Actualizar gauges
        self.temp_gauge.setValue(int(t_last))
        self.hum_gauge.setValue(int(h_last))
        self.lux_gauge.setValue(int(l_last))

        # Stats
        t_mean = stats.fmean(temps)
        t_min = min(temps)
        t_max = max(temps)
        self.lbl_temp_stats.setText(
            f"μ: {t_mean:.1f}   min: {t_min:.1f}   max: {t_max:.1f}"
        )

        h_mean = stats.fmean(hums)
        h_min = min(hums)
        h_max = max(hums)
        self.lbl_hum_stats.setText(
            f"μ: {h_mean:.1f}   min: {h_min:.1f}   max: {h_max:.1f}"
        )

        l_mean = stats.fmean(luxs)
        l_min = min(luxs)
        l_max = max(luxs)
        self.lbl_lux_stats.setText(
            f"μ: {l_mean:.0f}   min: {l_min:.0f}   max: {l_max:.0f}"
        )

        # Colorear gauges según valor (SCADA style)
        self._color_gauge_temp(t_last)
        self._color_gauge_hum(h_last)
        self._color_gauge_lux(l_last)

    # ====== COLOR DE GAUGES (SCADA/HMI) ======
    def _color_gauge_temp(self, value: float) -> None:
        if value >= self.ALERT_TEMP_CRITICAL:
            # Rojo
            self.temp_gauge.setStyleSheet(
                "QProgressBar::chunk { background-color: #ff3b30; }"
            )
        elif value >= self.ALERT_TEMP_HIGH:
            # Ámbar
            self.temp_gauge.setStyleSheet(
                "QProgressBar::chunk { background-color: #ffcc00; }"
            )
        else:
            # Verde
            self.temp_gauge.setStyleSheet(
                "QProgressBar::chunk { background-color: #34c759; }"
            )

    def _color_gauge_hum(self, value: float) -> None:
        if value <= self.ALERT_HUM_CRITICAL:
            self.hum_gauge.setStyleSheet(
                "QProgressBar::chunk { background-color: #ff3b30; }"
            )
        elif value <= self.ALERT_HUM_LOW:
            self.hum_gauge.setStyleSheet(
                "QProgressBar::chunk { background-color: #ffcc00; }"
            )
        else:
            self.hum_gauge.setStyleSheet(
                "QProgressBar::chunk { background-color: #34c759; }"
            )

    def _color_gauge_lux(self, value: float) -> None:
        if value >= self.ALERT_LUX_CRITICAL:
            self.lux_gauge.setStyleSheet(
                "QProgressBar::chunk { background-color: #ff3b30; }"
            )
        elif value >= self.ALERT_LUX_HIGH:
            self.lux_gauge.setStyleSheet(
                "QProgressBar::chunk { background-color: #ffcc00; }"
            )
        else:
            self.lux_gauge.setStyleSheet(
                "QProgressBar::chunk { background-color: #34c759; }"
            )
    # ===================== ALERTAS INTELIGENTES =====================
    def _update_alerts(self) -> None:
        if not self.readings:
            return

        last = self.readings[-1]
        t = last.temperature
        h = last.humidity
        l = last.luminosity

        critical = False
        warning = False
        messages: List[str] = []

        # Temperatura
        if t >= self.ALERT_TEMP_CRITICAL:
            critical = True
            messages.append(f"T alta CRÍTICA ({t:.1f} °C)")
        elif t >= self.ALERT_TEMP_HIGH:
            warning = True
            messages.append(f"T alta ({t:.1f} °C)")

        # Humedad
        if h <= self.ALERT_HUM_CRITICAL:
            critical = True
            messages.append(f"H baja CRÍTICA ({h:.1f} %)")
        elif h <= self.ALERT_HUM_LOW:
            warning = True
            messages.append(f"H baja ({h:.1f} %)")

        # Lux
        if l >= self.ALERT_LUX_CRITICAL:
            critical = True
            messages.append(f"Luz ALTA CRÍTICA ({l:.0f} lux)")
        elif l >= self.ALERT_LUX_HIGH:
            warning = True
            messages.append(f"Luz alta ({l:.0f} lux)")

        # Texto y nivel final
        if critical:
            level = "critical"
            full_msg = " | ".join(messages)
            self.alert_label.setText("⚠ ALERTA CRÍTICA: " + full_msg)
            self._set_alert_style("critical")
            self.statusBar().showMessage("ALERTA CRÍTICA: " + full_msg, 5000)

            # 👉 Guardar alerta en la base de datos
            self.db.insert_alert(level=level, message=full_msg, reading=last)

        elif warning:
            level = "warning"
            full_msg = " | ".join(messages)
            self.alert_label.setText("⚠ ALERTA: " + full_msg)
            self._set_alert_style("warning")
            self.statusBar().showMessage("Alerta: " + full_msg, 5000)

            # 👉 Guardar alerta en la base de datos
            self.db.insert_alert(level=level, message=full_msg, reading=last)

        else:
            level = "normal"
            self.alert_label.setText("Estado del sistema: NORMAL")
            self._set_alert_style("normal")
            # Si quieres guardar también los estados normales, descomenta:
            # self.db.insert_alert(level=level, message="Estado normal", reading=last)
    
    def _set_alert_style(self, level: str) -> None:
        """Cambia los colores del panel de alerta según el nivel."""
        if level == "critical":
            # Rojo
            self.alert_label.setStyleSheet(
                "background-color: #ff3b30; color: white; font-weight: 700; padding: 4px; border-radius: 4px;"
            )
        elif level == "warning":
            # Ámbar
            self.alert_label.setStyleSheet(
                "background-color: #ffcc00; color: black; font-weight: 700; padding: 4px; border-radius: 4px;"
            )
        else:
            # Verde (normal)
            self.alert_label.setStyleSheet(
                "background-color: #34c759; color: black; font-weight: 700; padding: 4px; border-radius: 4px;"
            )

    # ===================== GRÁFICAS =====================
    def _clear_axes(self) -> None:
        self.ax_temp.clear()
        self.ax_hum.clear()
        self.ax_lux.clear()
        self.canvas.draw()

    def _update_plots(self) -> None:
        if not self.readings:
            return

        data = self.readings[-self.stats_window :]

        times = [r.timestamp for r in data]
        temps = [r.temperature for r in data]
        hums = [r.humidity for r in data]
        luxs = [r.luminosity for r in data]

        self.ax_temp.clear()
        self.ax_hum.clear()
        self.ax_lux.clear()

        self.ax_temp.plot(times, temps)
        self.ax_temp.set_ylabel("Temp (°C)")
        self.ax_temp.grid(True)

        self.ax_hum.plot(times, hums)
        self.ax_hum.set_ylabel("Humedad (%)")
        self.ax_hum.grid(True)

        self.ax_lux.plot(times, luxs)
        self.ax_lux.set_ylabel("Lux")
        self.ax_lux.set_xlabel("Tiempo")
        self.ax_lux.grid(True)

        self.figure.autofmt_xdate()
        self.canvas.draw()

    def _reset_plots(self) -> None:
        self.readings.clear()
        self._clear_axes()
        self._reset_indicators()
        self.info_label.setText("Gráficas reseteadas. Vuelve a iniciar la lectura.")
        self.statusBar().showMessage("Gráficas reseteadas.", 2000)

    # ===================== EXPORTAR A EXCEL =====================
    def export_excel(self) -> None:
        output_str, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar histórico a Excel",
            "sensor_data.xlsx",
            "Excel (*.xlsx)",
        )
        if not output_str:
            return

        try:
            export_to_excel(self.db, Path(output_str))
            QMessageBox.information(
                self,
                "Exportación",
                f"Datos exportados correctamente a:\n{output_str}",
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"No se pudo exportar a Excel:\n{e}"
            )

    # ===================== MODO OSCURO / CLARO =====================
    def toggle_dark_mode(self, state: int) -> None:
        enabled = state == Qt.Checked
        self.settings.set("dark_mode", enabled)
        if enabled:
            self._apply_dark_palette()
        else:
            self._apply_light_palette()

    def _apply_dark_palette(self) -> None:
        dark_style = """
        QSpinBox {
            background-color: #3a3a3a;
            color: #ffffff;
            border: 1px solid #666;
            border-radius: 4px;
            padding: 2px 6px;
            min-width: 80px;
        }

        QMainWindow {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QPushButton {
            background-color: #3a3a3a;
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px 10px;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QPushButton:disabled {
            background-color: #2b2b2b;
            color: #777777;
        }
        QCheckBox {
            color: #ffffff;
        }
        #indicatorsFrame {
            background-color: #3a3a3a;
            border-radius: 6px;
        }
        #alertFrame {
            background-color: transparent;
        }
        """
        self.setStyleSheet(dark_style)

    def _apply_light_palette(self) -> None:
        light_style = """

        QSpinBox {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #888;
            border-radius: 4px;
            padding: 2px 6px;
            min-width: 80px;
        }
        QMainWindow {
            background-color: #e3e0dc;
            color: #000000;
        }
        QWidget {
            background-color: #ffffff;
            color: #000000;
        }
        QPushButton {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #aaa;
            border-radius: 4px;
            padding: 4px 10px;
        }
        QPushButton:hover {
            background-color: #f0f0f0;
        }
        QPushButton:disabled {
            background-color: #dddddd;
            color: #888888;
        }
        QCheckBox {
            color: #000000;
        }
        #indicatorsFrame {
            background-color: #ffffff;
            border-radius: 6px;
        }
        #alertFrame {
            background-color: transparent;
        }
        """
        self.setStyleSheet(light_style)
