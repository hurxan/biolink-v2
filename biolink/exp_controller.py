# -*- coding: utf-8 -*-
"""Experiment control: PLUX, serial events, logging, extensions."""

import csv
import json
import os
import threading
import time
from multiprocessing import Pipe
from random import randint

import numpy as np
import serial
import serial.tools.list_ports

from biolink import msg_logger as MsgLogger
from biolink import plux_interface as PluxInterface
from biolink import realtime_plot as RealtimePlot
from biolink.constants import (
    MAX_CHANNEL_CNT,
    MAX_EXTENSION_EVENT_STR_LEN,
    MAX_SERIAL_EVENT_STR_LEN,
)
from biolink.extension_interface import ExtensionInterfaceFrontend

versionStr = "V1.1"

pluxMac = "00:07:80:79:6F:E0"
fs = 1000

maxDurationFrames = 3600 * fs

channelHeader = ["ecg", "eda", "bvp"]
channelMask = 0x07
bitsResolution = 16

if os.name == "nt":
    serialPort = "COM1"
else:
    serialPort = "/dev/ttyUSB0"
serialBaud = 115200

PLOT_RANGE_SEC = 10
plotRefreshRate = 1

pluxDevice = None
logRawFile = None
logRawCsvWriter = None
ser = None
isSerialOpen = threading.Event()
stopSerialReconnectThread = threading.Event()
nolog = False
endLogging = threading.Event()
notifyExpEndFnc = None
deviceThread = None
logThread = None
serialReconnectThread = None
tmpEventStr = ""
startTime = None
logFileNameBase = None
extInterface = None

versionStr = ""
logDir = "../log/"
subjectId = ""
experimentId = ""
useSerial = True
useLifePlot = True
reopenLifePlot = True
extensionName = "None"

bioData = None
serialEventData = None
extensionEventData = None
frameCnt = 0


def _serial_buf_to_str(buf):
    if isinstance(buf, bytes):
        return buf.decode("latin-1")
    return buf


def pluxOpenDevice():
    global pluxDevice, pluxMac

    pluxCloseDevice()
    closePlot()
    time.sleep(0.1)

    pluxDevice = PluxInterface.openDevice(pluxMac)
    props = pluxDevice.getProperties()
    MsgLogger.append("Plux Device: " + str(props))
    MsgLogger.append("Plux Device Battery: " + pluxDevice.getBatteryStr())


def pluxStartDeviceLoop(pipeEnd):
    global pluxDevice
    pluxDevice.stopRequest.clear()
    pluxDevice.pipeConn = pipeEnd
    pluxDevice.start(fs, channelMask, bitsResolution)
    pluxDevice.loop()
    print("Plux device loop terminated")
    pluxDevice.stop()
    pluxCloseDevice()


def pluxCloseDevice():
    global pluxDevice
    if pluxDevice:
        MsgLogger.append("Plux Device Battery: " + pluxDevice.getBatteryStr())
        pluxDevice.close()
        del pluxDevice
    pluxDevice = None


def configChannels(channelNames):
    global channelHeader, channelMask

    channelHeader = []
    channelMask = 0
    index = 0

    for name in channelNames:
        if name != "":
            channelHeader.append(name)
            channelMask |= 0x01 << index
        index += 1


def serialOpen(exceptionOnError):
    global ser, isSerialOpen

    try:
        ser = serial.Serial(serialPort, serialBaud, timeout=0)
        if ser:
            isSerialOpen.set()
            return True
    except Exception:
        ser = None
        isSerialOpen.clear()
        if exceptionOnError:
            raise
        return False


def serialClose():
    global ser, isSerialOpen, tmpEventStr
    if ser:
        ser.close()
        ser = None
        tmpEventStr = ""
        isSerialOpen.clear()


def serialEnumPorts():
    l = list(serial.tools.list_ports.comports())
    l.sort()
    return l


def _serialReconnectLoop():
    global stopSerialReconnectThread
    while not stopSerialReconnectThread.is_set():
        if not isSerialOpen.is_set():
            serialOpen(False)
        time.sleep(1)


def serialStartReconnectThread():
    global stopSerialReconnectThread, serialReconnectThread
    stopSerialReconnectThread.clear()
    serialReconnectThread = threading.Thread(target=_serialReconnectLoop, daemon=True)
    serialReconnectThread.start()


def _serialAssembleEvent(buf, startSeq=None, endSeq="\n"):
    global tmpEventStr
    startIndex = 0
    startStrLen = 0
    retval = None

    buf = _serial_buf_to_str(buf)
    tmpEventStr = tmpEventStr + buf
    print("tmpEventStr before: '" + repr(tmpEventStr) + "'")

    if startSeq:
        startStrLen = len(startSeq)
        startIndex = tmpEventStr.find(startSeq)

    if startIndex >= 0:
        endIndex = tmpEventStr.find(endSeq, startIndex)
        print("startIndex", startIndex)

        if endIndex >= 0:
            print("endIndex", endIndex)
            retval = tmpEventStr[startIndex + startStrLen : endIndex]
            if len(retval) > MAX_SERIAL_EVENT_STR_LEN:
                retval = retval[0 : MAX_SERIAL_EVENT_STR_LEN - 1]
            tmpEventStr = tmpEventStr[endIndex + len(endSeq) :]
    print("tmpEventStr after: '" + repr(tmpEventStr) + "'")

    return retval


def _serialHandleSpecialEvents(event):
    if event == "#END":
        stopExperiment()


def serialCheckEvent(curFrameNr):
    global ser, isSerialOpen, serialEventData

    retval = False

    if isSerialOpen.is_set():
        if not serialCheckEvent.oldIsSerialOpen:
            MsgLogger.append("Serial port reconnected.")
            serialEventData.append((curFrameNr, "#reconn"))
            serialCheckEvent.oldIsSerialOpen = True
        try:
            buf = ser.read(50)
            if len(buf) > 0:
                while True:
                    event = _serialAssembleEvent(buf)
                    if event:
                        serialEventData.append((curFrameNr, event))
                        MsgLogger.append(
                            "Serial event at frame nr "
                            + str(curFrameNr)
                            + ": '"
                            + event
                            + "'"
                        )
                        _serialHandleSpecialEvents(event)
                        retval = True
                        buf = ""
                    else:
                        break
        except Exception:
            MsgLogger.append("No connection to serial port.")
            serialEventData.append((curFrameNr, "#noconn"))
            serialClose()
            serialCheckEvent.oldIsSerialOpen = False

    return retval


serialCheckEvent.oldIsSerialOpen = True


def serialReceiveSubjectId():
    global ser, isSerialOpen

    if isSerialOpen.is_set():
        buf = ser.read(20)
        if len(buf) > 0:
            s_id = _serialAssembleEvent(buf, "#ID:", "\n")
            if s_id:
                return s_id

    return ""


def extensionStart():
    global extInterface

    extInterface = ExtensionInterfaceFrontend(
        subjectId,
        experimentId,
        logDir,
        startTime,
        logFileNameBase,
        channelHeader,
        fs,
        nolog,
    )
    if extInterface.selectExtensionByName(extensionName):
        extInterface.extensionStart()
    else:
        MsgLogger.append("Error opening extension '" + extensionName + "'.")


def extensionEnd():
    global extInterface

    if extInterface:
        extInterface.extensionEnd()
        extInterface = None


def extensionCheckEvent(curFrameNr):
    global extInterface, extensionEventData

    if extInterface:
        event_list = extInterface.checkEvents(curFrameNr)
        if len(event_list) > 0:
            for frame_nr, e in event_list:
                if frame_nr < 0:
                    stopExperiment()
                else:
                    if len(e) > MAX_EXTENSION_EVENT_STR_LEN:
                        e = e[0 : MAX_EXTENSION_EVENT_STR_LEN - 1]
                    extensionEventData.append((frame_nr, e))
                    MsgLogger.append(
                        "Extension event at frame nr "
                        + str(frame_nr)
                        + ": '"
                        + e
                        + "'"
                    )


def setMaxDuration(minutes):
    global maxDurationFrames
    maxDurationFrames = minutes * 60 * fs


def _expEnded():
    global stopSerialReconnectThread, tmpEventStr, notifyExpEndFnc, deviceThread

    stopSerialReconnectThread.set()
    tmpEventStr = ""

    _safeLog()

    deviceThread.join(timeout=5)

    if notifyExpEndFnc:
        notifyExpEndFnc()


def _safeLog(appendToFileName=""):
    global serialEventData, bioData, extensionEventData, channelHeader

    if not nolog:
        npzPath = logFileNameBase + appendToFileName + ".npz"
        jsonPath = logFileNameBase + appendToFileName + ".json"

        logChannelHeader = np.array(channelHeader)
        bioData = bioData[:frameCnt]
        serialEventDataArr = np.array(
            serialEventData,
            np.dtype(
                [
                    ("frame_nr", np.uint32),
                    ("event_str", "S" + str(MAX_SERIAL_EVENT_STR_LEN)),
                ]
            ),
        )

        extensionEventData.sort(key=lambda l: l[0])
        extensionEventDataArr = np.array(
            extensionEventData,
            np.dtype(
                [
                    ("frame_nr", np.uint32),
                    ("event_str", "S" + str(MAX_EXTENSION_EVENT_STR_LEN)),
                ]
            ),
        )

        np.savez_compressed(
            npzPath,
            channelHeader=logChannelHeader,
            bioData=bioData,
            serialEventData=serialEventDataArr,
            extensionEventData=extensionEventDataArr,
        )
        MsgLogger.append("Data saved to '" + npzPath + "'")

        dateStr = time.strftime("%d/%m/%Y %H:%M", startTime)
        duration_sec = float(frameCnt) / fs
        hdrDict = {
            "version": versionStr,
            "dateStr": dateStr,
            "experimentId": experimentId,
            "subjectId": subjectId,
            "fs": fs,
            "frameCnt": frameCnt,
            "duration_sec": duration_sec,
            "channels": channelHeader,
            "pluxMac": pluxMac,
            "extension": extensionName,
        }
        with open(jsonPath, "w") as f:
            json.dump(hdrDict, f, indent=2)


def _expControlLoop(pipeConn):
    global bioData, serialEventData, frameCnt, endLogging

    try:
        while not endLogging.is_set():
            if pipeConn.poll(5):
                (curFrameNr, dataTup) = pipeConn.recv()

                if curFrameNr >= maxDurationFrames:
                    break

                serialCheckEvent(curFrameNr)
                extensionCheckEvent(curFrameNr)

                bioData[curFrameNr] = dataTup
                frameCnt = curFrameNr + 1

                if extInterface:
                    extInterface.putBioData(curFrameNr, dataTup)

                if useLifePlot:
                    RealtimePlot.plotDataFrame(float(curFrameNr) / fs, dataTup)

            else:
                MsgLogger.append(
                    "Error: no data from Plux device thread. Connection to Plux device lost."
                )
                break
    except Exception as e:
        MsgLogger.append("Error in _expControlLoop. Ending experiment.")
        print(e)

    pluxDevice.endAquisition()
    _expEnded()


def startExperiment(subjectIdStr):
    global bioData, serialEventData, frameCnt, deviceThread, logThread, tmpEventStr
    global startTime, subjectId, logFileNameBase, extensionEventData, nolog

    if pluxDevice is None:
        raise Exception("Error in startExperiment: Plux not opened.")

    subjectId = subjectIdStr
    if subjectId == "nolog":
        nolog = True
    else:
        nolog = False

    channelCnt = len(channelHeader)
    bioData = np.zeros((maxDurationFrames, channelCnt), np.uint16)
    serialEventData = []
    extensionEventData = []
    frameCnt = 0
    tmpEventStr = ""

    loggerConn, pluxConn = Pipe()
    endLogging.clear()
    serialCheckEvent.oldIsSerialOpen = True

    cfg = RealtimePlot.PlotConfig()
    cfg.channelCnt = channelCnt
    cfg.channelLabels = channelHeader
    cfg.xLabel = "Seconds"
    cfg.xRange = PLOT_RANGE_SEC
    cfg.yMin = 0
    cfg.yMax = 2**bitsResolution
    cfg.reopenPlotOnClose = reopenLifePlot

    deviceThread = threading.Thread(target=pluxStartDeviceLoop, args=(pluxConn,), daemon=True)
    logThread = threading.Thread(target=_expControlLoop, args=(loggerConn,), daemon=True)

    startTime = time.localtime()
    logFileNameBase = (
        logDir
        + experimentId
        + "_"
        + subjectId
        + "_"
        + time.strftime("%Y%m%d_%H%M", startTime)
    )

    deviceThread.start()
    if useLifePlot:
        RealtimePlot.startPlotProcess(cfg)
    logThread.start()
    if useSerial:
        serialStartReconnectThread()


def stopExperiment():
    endLogging.set()


def forceStopExperiment():
    global stopSerialReconnectThread, tmpEventStr, notifyExpEndFnc, deviceThread

    endLogging.set()
    pluxDevice.endAquisition()
    stopSerialReconnectThread.set()

    tmpEventStr = ""

    _safeLog("_forcedsave")

    pluxCloseDevice()

    if notifyExpEndFnc:
        notifyExpEndFnc()


def closePlot():
    RealtimePlot.terminatePlotProcess()
