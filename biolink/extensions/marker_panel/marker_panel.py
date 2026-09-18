# -*- coding: utf-8 -*-
"""
Demo extension: manual event markers aligned to PLUX frames.

Useful to test BioLink without PsychoPy or serial — e.g. with Plux MAC ``dummy``.
"""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from biolink.extensions.extension_base import ExtensionBase

MARKERS = [
    ("stim", "Stimulus"),
    ("resp", "Response"),
    ("fix", "Fixation"),
    ("iti", "ITI start"),
]


class MarkerWindow(QMainWindow):
    def __init__(self, extension: "ExtensionMarkerPanel"):
        super().__init__()
        self.ext = extension
        self.setWindowTitle("BioLink — marker panel (demo)")
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        info = QLabel(
            "Click a button to log an event on the PLUX timeline.\n"
            "Events appear in the main .npz (ExtensionEvent column) and in the extension .txt log."
        )
        info.setWordWrap(True)
        root.addWidget(info)

        status_box = QGroupBox("Live status")
        status_layout = QVBoxLayout(status_box)
        self.lbl_frame = QLabel("Frame: —")
        self.lbl_time = QLabel("Time [s]: —")
        self.lbl_bio = QLabel("Last sample: —")
        status_layout.addWidget(self.lbl_frame)
        status_layout.addWidget(self.lbl_time)
        status_layout.addWidget(self.lbl_bio)
        root.addWidget(status_box)

        markers_box = QGroupBox("Markers")
        grid = QGridLayout(markers_box)
        for i, (code, label) in enumerate(MARKERS):
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked=False, c=code: self.ext.mark_event(c))
            grid.addWidget(btn, i // 2, i % 2)
        root.addWidget(markers_box)

        auto_row = QHBoxLayout()
        self.btn_auto = QPushButton("Auto marker every 5 s")
        self.btn_auto.setCheckable(True)
        self.btn_auto.toggled.connect(self.ext.toggle_auto_marker)
        auto_row.addWidget(self.btn_auto)
        root.addLayout(auto_row)

        end_row = QHBoxLayout()
        end_row.addStretch()
        btn_end = QPushButton("End experiment")
        btn_end.clicked.connect(self.ext.request_end)
        end_row.addWidget(btn_end)
        root.addLayout(end_row)

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self.ext.refresh_status_labels)
        self._status_timer.start(200)

        self.resize(420, 380)


class ExtensionMarkerPanel(ExtensionBase):
    logColumnHeader = ["frameNr", "event", "time_sec"]
    extensionName = "marker_panel"

    def __init__(self, extensionInterfaceBackend, extConstants):
        super().__init__(extensionInterfaceBackend, extConstants)
        self.app = None
        self.window = None
        self._last_bio = None
        self._last_frame = -1
        self._auto_timer = None

    def mark_event(self, code: str):
        frame_nr = self.eib.putEvent(code)
        if frame_nr >= 0:
            t_sec = frame_nr / float(self.extConstants.sampleFreq)
            self.logAppendLine([frame_nr, code, f"{t_sec:.3f}"])
            self.eib.consoleMessage(
                f"marker_panel: '{code}' at frame {frame_nr} ({t_sec:.3f} s)"
            )

    def toggle_auto_marker(self, enabled: bool):
        if self._auto_timer is None:
            return
        if enabled:
            self._auto_timer.start(5000)
            self.eib.consoleMessage("marker_panel: auto marker every 5 s ON")
        else:
            self._auto_timer.stop()
            self.eib.consoleMessage("marker_panel: auto marker OFF")

    def _auto_tick(self):
        self.mark_event("auto5s")

    def refresh_status_labels(self):
        if not self.window:
            return
        fn = self.eib.getCurrentFramenr()
        if fn < 0:
            self.window.lbl_frame.setText("Frame: (waiting for data…)")
            self.window.lbl_time.setText("Time [s]: —")
        else:
            self.window.lbl_frame.setText(f"Frame: {fn}")
            self.window.lbl_time.setText(
                f"Time [s]: {fn / float(self.extConstants.sampleFreq):.3f}"
            )
        if self._last_bio is not None and self._last_frame >= 0:
            parts = [
                f"{self.extConstants.channelHeader[i]}={self._last_bio[i]}"
                for i in range(min(len(self._last_bio), len(self.extConstants.channelHeader)))
            ]
            self.window.lbl_bio.setText(
                f"Last sample (frame {self._last_frame}): " + ", ".join(parts)
            )

    def request_end(self):
        self.eib.endExperiment()

    def extMainLoop(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.window = MarkerWindow(self)
        self.window.show()

        self._auto_timer = QTimer()
        self._auto_timer.timeout.connect(self._auto_tick)

        self.startBioDataProcessing()
        self.app.exec()

    def _shutdown_ui(self):
        self.stopBioDataProcessing()
        if self._auto_timer:
            self._auto_timer.stop()
        if self.window:
            self.window.close()
        if self.app:
            self.app.quit()

    def onBioDataFrame(self, frameNr, bioDataTup):
        self._last_frame = frameNr
        self._last_bio = bioDataTup

    def onExtEndRequest(self):
        QTimer.singleShot(0, self._shutdown_ui)
