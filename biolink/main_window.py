# -*- coding: utf-8 -*-
"""Main window (PySide6)."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    console_append_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.console_append_requested.connect(self._append_console_main_thread)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(12, 12, 12, 12)

        self._build_menubar()

        settings_box = QGroupBox("Settings")
        form = QFormLayout(settings_box)
        form.setLabelAlignment(Qt.AlignRight)

        serial_row = QHBoxLayout()
        self.teSerialPort = QLineEdit()
        self.btFindSerial = QPushButton("find ports")
        serial_row.addWidget(self.teSerialPort)
        serial_row.addWidget(self.btFindSerial)
        form.addRow("Serial Port:", serial_row)

        self.cbUseSerial = QCheckBox("Use Serial Port")
        form.addRow("", self.cbUseSerial)

        plux_row = QHBoxLayout()
        self.tePluxMac = QLineEdit()
        self.btFindPlux = QPushButton("find devices")
        plux_row.addWidget(self.tePluxMac)
        plux_row.addWidget(self.btFindPlux)
        form.addRow("Plux MAC:", plux_row)

        self.teChannelNames = QLineEdit()
        form.addRow("Channel Names:", self.teChannelNames)

        self.teSampleRate = QLineEdit()
        form.addRow("Sample Rate [Hz]:", self.teSampleRate)

        self.teMaxDuration = QLineEdit()
        form.addRow("Max Duration [min]:", self.teMaxDuration)

        self.cbUseLifePlot = QCheckBox("Paint Life Plot")
        form.addRow("Life Plot:", self.cbUseLifePlot)

        self.cbReopenLifePlot = QCheckBox("Reopen Life Plot if closed")
        form.addRow("", self.cbReopenLifePlot)

        self.cbExtension = QComboBox()
        form.addRow("Extension:", self.cbExtension)

        root.addWidget(settings_box)

        exp_box = QGroupBox("Experiment")
        exp_form = QFormLayout(exp_box)
        self.teExperimentId = QLineEdit()
        exp_form.addRow("Experiment ID:", self.teExperimentId)

        subject_row = QHBoxLayout()
        self.teSubjectId = QLineEdit()
        self.btStart = QPushButton("start")
        self.btEnd = QPushButton("end")
        self.btStart.setDefault(True)
        subject_row.addWidget(self.teSubjectId)
        subject_row.addStretch()
        subject_row.addWidget(self.btStart)
        subject_row.addWidget(self.btEnd)
        exp_form.addRow("Subject ID:", subject_row)
        root.addWidget(exp_box)

        root.addWidget(QLabel("Messages:"))
        self.tvConsole = QTextEdit()
        self.tvConsole.setReadOnly(True)
        self.tvConsole.setMinimumHeight(140)
        root.addWidget(self.tvConsole, stretch=1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(central)
        self.setCentralWidget(scroll)

        self.teSubjectId.setToolTip(
            "Subject ID\nTESTING: enter 'nolog' to not save a log"
        )
        self.tePluxMac.setToolTip(
            "MAC address of format: xx:xx:xx:xx:xx:xx\nTESTING: enter 'dummy' for dummy data"
        )

        self.freeze_objects = [
            self.teSerialPort,
            self.tePluxMac,
            self.teChannelNames,
            self.teExperimentId,
            self.teSubjectId,
            self.btFindSerial,
            self.btFindPlux,
            self.teSampleRate,
            self.teMaxDuration,
            self.cbUseSerial,
            self.cbUseLifePlot,
            self.cbReopenLifePlot,
            self.cbExtension,
        ]

        self.setMinimumSize(640, 520)

    def _build_menubar(self):
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        tools_menu = menubar.addMenu("&Tools")
        act_convert = QAction("&Convert log to txt", self)
        act_plot = QAction("&Plot BioLink Data", self)
        tools_menu.addAction(act_convert)
        tools_menu.addAction(act_plot)

        settings_menu = menubar.addMenu("&Settings")
        act_defaults = QAction("&Default Values", self)
        settings_menu.addAction(act_defaults)

        self._menu_actions = {
            "convert": act_convert,
            "plot": act_plot,
            "defaults": act_defaults,
        }

    def init_extension_combo_box(self, ext_name_list):
        self.cbExtension.clear()
        for name in ext_name_list:
            self.cbExtension.addItem(name)
        self.cbExtension.setCurrentIndex(0)

    def console_append(self, msg):
        self.console_append_requested.emit(str(msg))

    def _append_console_main_thread(self, msg):
        self.tvConsole.append(msg)
        sb = self.tvConsole.verticalScrollBar()
        sb.setValue(sb.maximum())

    def freeze_settings(self, freeze):
        enabled = not freeze
        for obj in self.freeze_objects:
            obj.setEnabled(enabled)

    def set_window_title_text(self, title):
        self.setWindowTitle(title)
