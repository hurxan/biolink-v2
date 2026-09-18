# -*- coding: utf-8 -*-
"""UI event handlers and experiment workflow."""

import threading

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
)

from biolink import exp_controller as ExpController
from biolink import log_tools as LogTools
from biolink import msg_logger as MsgLogger
from biolink import plux_interface as PluxInterface
from biolink import prevent_sleep as PreventSleep
from biolink.extension_interface import enumerateExtensionNames
from biolink.main_window import MainWindow
from biolink.paths import LOG_DIR, LOG_DIR_STR, SETTINGS_FILE
from biolink.settings_model import settingsModel

SETTINGS_FILE_PATH = str(SETTINGS_FILE)

isExperimentRunning = False
subjectId = ""
extNameList = None
_emergencyTimeoutId = None
_view = None


def bind_view(view: MainWindow):
    global _view
    _view = view
    view.btStart.clicked.connect(start_experiment)
    view.btEnd.clicked.connect(end_experiment)
    view.btFindSerial.clicked.connect(find_serial_ports)
    view.btFindPlux.clicked.connect(find_plux_devices)
    view._menu_actions["defaults"].triggered.connect(reset_settings)
    view._menu_actions["convert"].triggered.connect(convert_log_to_txt)
    view._menu_actions["plot"].triggered.connect(plot_biolink_data)


def init():
    global extNameList

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    extNameList = enumerateExtensionNames()
    extNameList.insert(0, "None")

    _view.btStart.setEnabled(True)
    _view.btEnd.setEnabled(False)
    _view.init_extension_combo_box(extNameList)

    load_settings()
    set_view_settings_from_model()

    ExpController.logDir = LOG_DIR_STR
    ExpController.notifyExpEndFnc = _end_experiment_callback


def on_delete_window():
    if isExperimentRunning:
        warning_dialog("Please end the current experiment before closing.")
        return True
    update_model_with_settings()
    save_settings()
    ExpController.closePlot()
    ExpController.serialClose()
    return False


def _exception_message(e):
    return getattr(e, "message", None) or str(e)


def start_experiment():
    global isExperimentRunning, subjectId

    if update_model_with_settings():
        subjectId = _view.teSubjectId.text().strip()

        ExpController.configChannels(settingsModel.settingsDict["channelNames"])
        ExpController.serialPort = settingsModel.settingsDict["serialPort"]
        ExpController.experimentId = settingsModel.settingsDict["experimentId"]
        ExpController.pluxMac = settingsModel.settingsDict["pluxMac"]
        ExpController.fs = settingsModel.settingsDict["sampleRate"]
        ExpController.setMaxDuration(settingsModel.settingsDict["maxDuration"])
        ExpController.useSerial = settingsModel.settingsDict["useSerial"]
        ExpController.useLifePlot = settingsModel.settingsDict["useLifePlot"]
        ExpController.reopenLifePlot = settingsModel.settingsDict["reopenLifePlot"]
        ExpController.extensionName = settingsModel.settingsDict["extension"]

        progress = QProgressDialog(
            "Opening Plux device. This can take a few seconds...",
            None,
            0,
            0,
            _view,
        )
        progress.setWindowModality(Qt.ApplicationModal)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()

        try:
            ExpController.pluxOpenDevice()
        except Exception as e:
            progress.close()
            MsgLogger.append("Error opening Plux device: " + _exception_message(e))
            warning_dialog("Error opening Plux device: " + _exception_message(e))
            return
        progress.close()

        PreventSleep.preventSleep()

        if settingsModel.settingsDict["useSerial"]:
            try:
                ExpController.serialOpen(True)
            except Exception as e:
                MsgLogger.append("Error opening serial port: " + _exception_message(e))

        if subjectId == "":
            if ExpController.isSerialOpen.is_set():
                receive_subject_id_from_serial()
            else:
                warning_dialog("Please enter Subject ID or attach serial port.")

        if subjectId != "":
            _view.btStart.setEnabled(False)
            _view.btEnd.setEnabled(True)
            _view.freeze_settings(True)

            save_settings()

            isExperimentRunning = True
            MsgLogger.append("Start experiment with Subject ID: '" + subjectId + "'")

            ExpController.startExperiment(subjectId)
            ExpController.extensionStart()
        else:
            ExpController.serialClose()
            ExpController.pluxCloseDevice()
            PreventSleep.allowSleep()


def _end_experiment_callback():
    QTimer.singleShot(0, _end_experiment)


def _end_experiment():
    global isExperimentRunning, _emergencyTimeoutId

    ExpController.extensionEnd()
    ExpController.serialClose()

    _view.btStart.setEnabled(True)
    _view.btEnd.setEnabled(False)
    _view.freeze_settings(False)
    _view.teSubjectId.setText("")

    isExperimentRunning = False
    if _emergencyTimeoutId is not None:
        _emergencyTimeoutId.stop()
        _emergencyTimeoutId = None

    MsgLogger.append("Experiment ended")
    PreventSleep.allowSleep()


def _end_experiment_detect_emergency():
    if isExperimentRunning:
        ExpController.forceStopExperiment()


def end_experiment():
    global _emergencyTimeoutId
    ExpController.stopExperiment()
    _emergencyTimeoutId = QTimer()
    _emergencyTimeoutId.setSingleShot(True)
    _emergencyTimeoutId.timeout.connect(_end_experiment_detect_emergency)
    _emergencyTimeoutId.start(11000)


def find_serial_ports():
    port_list = ExpController.serialEnumPorts()
    msg = "Serial Ports:"
    if len(port_list) == 0:
        msg = msg + " no ports found"
    else:
        for p in port_list:
            msg = msg + "\n\t" + p[0] + ": " + p[1]
    MsgLogger.append(msg)


def find_plux_devices():
    ExpController.closePlot()

    progress = QProgressDialog(
        "Searching Plux devices. This can take a few seconds...",
        None,
        0,
        0,
        _view,
    )
    progress.setWindowModality(Qt.ApplicationModal)
    progress.setMinimumDuration(0)
    progress.show()
    QApplication.processEvents()

    msg = "Plux Devices:"
    try:
        device_tuple = PluxInterface.enumDevices()
        if len(device_tuple) == 0:
            msg = msg + " no devices found"
        else:
            for d in device_tuple:
                msg = msg + "\n\t" + d[0] + ": " + d[1]
    except Exception as e:
        msg = msg + " " + str(e)

    progress.close()
    MsgLogger.append(msg)


def convert_log_to_txt():
    open_file, _ = QFileDialog.getOpenFileName(
        _view,
        "Please choose a log file",
        LOG_DIR_STR,
        "npz files (*.npz)",
    )
    if not open_file:
        return
    base_name = open_file[:-4] if open_file.lower().endswith(".npz") else open_file

    save_file, _ = QFileDialog.getSaveFileName(
        _view,
        "Choose location for txt file",
        LOG_DIR_STR,
        "Text files (*.txt)",
    )
    if not save_file:
        return
    if not save_file.endswith(".txt"):
        save_file = save_file + ".txt"

    converter = threading.Thread(
        target=_converter_thread, args=(base_name, save_file), daemon=True
    )
    converter.start()


def _converter_thread(base_name, save_file):
    LogTools.exportTxt(base_name, save_file)
    MsgLogger.append("Converted '" + base_name + ".npz' to '" + save_file + "'")


def plot_biolink_data():
    open_file, _ = QFileDialog.getOpenFileName(
        _view,
        "Please choose a log file",
        LOG_DIR_STR,
        "npz files (*.npz)",
    )
    if not open_file:
        return
    base_name = open_file[:-4] if open_file.lower().endswith(".npz") else open_file
    LogTools.plotBioLinkData(base_name)


def update_model_with_settings():
    errcnt = 0

    d = {
        "serialPort": _view.teSerialPort.text().strip(),
        "pluxMac": _view.tePluxMac.text().strip(),
        "experimentId": _view.teExperimentId.text().strip(),
        "useSerial": _view.cbUseSerial.isChecked(),
        "useLifePlot": _view.cbUseLifePlot.isChecked(),
        "reopenLifePlot": _view.cbReopenLifePlot.isChecked(),
        "extension": extNameList[_view.cbExtension.currentIndex()],
    }
    settingsModel.updateSettings(d)

    success = settingsModel.setChannelNamesStr(_view.teChannelNames.text())
    if success:
        if len(settingsModel.settingsDict["channelNames"]) == 0:
            success = False

    if not success:
        warning_dialog("Invalid Channel Names. Please review settings.")
        errcnt += 1

    if not settingsModel.setMaxDurationStr(_view.teMaxDuration.text()):
        errcnt += 1
        warning_dialog("Invalid Max. Duration. Please review settings.")

    if not settingsModel.setSampleRateStr(_view.teSampleRate.text()):
        errcnt += 1
        warning_dialog("Invalid Sample Rate. Please review settings.")

    set_view_settings_from_model()

    return errcnt == 0


def set_view_settings_from_model():
    _view.teSerialPort.setText(settingsModel.settingsDict["serialPort"])
    _view.tePluxMac.setText(settingsModel.settingsDict["pluxMac"])
    _view.teExperimentId.setText(settingsModel.settingsDict["experimentId"])
    _view.teChannelNames.setText(settingsModel.getChannelNamesStr())
    _view.teMaxDuration.setText(settingsModel.getMaxDurationStr())
    _view.teSampleRate.setText(settingsModel.getSampleRateStr())
    _view.cbUseSerial.setChecked(settingsModel.settingsDict["useSerial"])
    _view.cbUseLifePlot.setChecked(settingsModel.settingsDict["useLifePlot"])
    _view.cbReopenLifePlot.setChecked(settingsModel.settingsDict["reopenLifePlot"])

    ext = settingsModel.settingsDict["extension"]
    if ext in extNameList:
        _view.cbExtension.setCurrentIndex(extNameList.index(ext))
    else:
        _view.cbExtension.setCurrentIndex(0)


def reset_settings():
    settingsModel.setToDefaultValues()
    set_view_settings_from_model()


def load_settings():
    try:
        with open(SETTINGS_FILE_PATH, "r") as f:
            settingsModel.loadSettings(f)
    except Exception as e:
        MsgLogger.append("Error loading '" + SETTINGS_FILE_PATH + "': " + str(e))


def save_settings():
    try:
        with open(SETTINGS_FILE_PATH, "w") as f:
            settingsModel.dumpSettings(f)
    except Exception:
        MsgLogger.append("Error saving to '" + SETTINGS_FILE_PATH + "'.")


def warning_dialog(msg):
    QMessageBox.warning(_view, "BioLink", msg)


def receive_subject_id_from_serial():
    global subjectId

    dialog = QDialog(_view)
    dialog.setWindowTitle("BioLink")
    layout = QVBoxLayout(dialog)
    layout.addWidget(
        QLabel("No Subject ID was entered. Waiting to receive Subject ID on serial port.")
    )
    cancel_btn = QPushButton("Cancel")
    cancel_btn.clicked.connect(dialog.reject)
    layout.addWidget(cancel_btn)

    end_timer = {"value": False}

    def timer_callback():
        global subjectId
        if end_timer["value"]:
            return
        try:
            subjectId = ExpController.serialReceiveSubjectId()
        except Exception:
            MsgLogger.append("Error receiving Subject ID.")
            dialog.reject()
            return
        if subjectId != "":
            dialog.accept()
        else:
            QTimer.singleShot(100, timer_callback)

    QTimer.singleShot(100, timer_callback)
    result = dialog.exec()
    dialog.deleteLater()

    if result != QDialog.Accepted:
        end_timer["value"] = True
        subjectId = ""
    else:
        _view.teSubjectId.setText(subjectId)
