# -*- coding: utf-8 -*-
"""Template extension (PySide6 dialog in extension subprocess)."""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from biolink.extensions.extension_base import ExtensionBase


class TemplateDialog(QDialog):
    def __init__(self, extension):
        super().__init__()
        self.extension = extension
        self.setWindowTitle("template extension")
        self.base_label = QLabel(
            "This Dialog is displayed by the BioLink template extension."
        )
        self.detail_label = QLabel("")
        layout = QVBoxLayout(self)
        layout.addWidget(self.base_label)
        layout.addWidget(self.detail_label)
        btn_row = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(lambda: self.extension.onDialogResponse("OK"))
        cancel_btn.clicked.connect(lambda: self.extension.onDialogResponse("cancel"))
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def closeEvent(self, event):
        self.extension.onDialogResponse("delete")
        event.accept()


class ExtensionTemplate(ExtensionBase):
    logColumnHeader = ["frameNr", "event"]
    extensionName = "template"

    def __init__(self, extensionInterfaceBackend, extConstants):
        super().__init__(extensionInterfaceBackend, extConstants)
        self.app = None
        self.dialog = None
        self.lastFrameNr = -1

    def onDialogResponse(self, responseId):
        if responseId == "OK":
            event = "OK"
        elif responseId == "cancel":
            event = "cancel"
        elif responseId == "delete":
            event = "delete"
            self.eib.endExperiment()
        else:
            event = str(responseId)

        forceFrameNr = None
        if event == "cancel":
            forceFrameNr = 123

        frameNr = self.eib.putEvent(event, frameNr=forceFrameNr)
        self.logAppendLine([frameNr, event])

        if event == "delete":
            self._endTemplateExt()

    def extMainLoop(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.dialog = TemplateDialog(self)
        self._updateDialogMsg("")
        self.dialog.show()
        self.lastFrameNr = -1
        self.startBioDataProcessing()
        self.app.exec()

    def _endTemplateExt(self):
        self.stopBioDataProcessing()
        if self.dialog:
            self.dialog.close()
        if self.app:
            self.app.quit()

    def _updateDialogMsg(self, msg):
        if self.dialog and self.dialog.isVisible():
            self.dialog.detail_label.setText(msg)

    def onBioDataFrame(self, frameNr, bioDataTup):
        if self.lastFrameNr == frameNr:
            print("Frame transmitted twice:", frameNr, bioDataTup)
        self.lastFrameNr = frameNr

        if frameNr % (self.extConstants.sampleFreq // 4) == 0:
            dataStr = "Frame: " + str(frameNr) + "  Bio Data:"
            for i in range(len(self.extConstants.channelHeader)):
                dataStr = (
                    dataStr
                    + "  "
                    + self.extConstants.channelHeader[i]
                    + ": "
                    + str(bioDataTup[i])
                )
            QTimer.singleShot(0, lambda m=dataStr: self._updateDialogMsg(m))

    def onExtEndRequest(self):
        QTimer.singleShot(0, self._endTemplateExt)
