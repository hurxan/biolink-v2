# -*- coding: utf-8 -*-
"""BioLink application entry (Python 3 + PySide6)."""

import sys
import time

from PySide6.QtWidgets import QApplication

from biolink import controller
from biolink import exp_controller as ExpController
from biolink import msg_logger as MsgLogger
from biolink.main_window import MainWindow
from biolink.paths import LOG_DIR

VERSION_STR = "BioLink_V1.4"
WND_TITLE = VERSION_STR.replace("_", " ")


def run():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setApplicationName("BioLink")
    app.setStyle("Fusion")

    view = MainWindow()

    def close_event(event):
        if controller.on_delete_window():
            event.ignore()
        else:
            MsgLogger.view_append_fnc = None
            MsgLogger.close()
            event.accept()

    view.closeEvent = close_event

    controller.bind_view(view)
    MsgLogger.view_append_fnc = view.console_append
    MsgLogger.init(str(LOG_DIR / ("BioLink_MsgLog_" + time.strftime("%Y%m%d_%H%M") + ".txt")))

    ExpController.versionStr = VERSION_STR
    controller.init()

    view.set_window_title_text(WND_TITLE)
    view.show()

    code = app.exec()
    sys.exit(code)


if __name__ == "__main__":
    run()
