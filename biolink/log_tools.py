# -*- coding: utf-8 -*-
"""Export and plot recorded BioLink data."""

import csv
import json
import multiprocessing as mp
import os

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backend_bases import MouseEvent

from biolink import msg_logger as MsgLogger

plotProc = None


def _field_as_str(val):
    if isinstance(val, bytes):
        return val.decode("latin-1")
    return str(val)


class BioLinkRawDataPlot:
    vLineX = 0.0
    vLineXold = 0.0
    axVLines = []

    def __init__(self, windowName, channelHeader, fs, data, serialEventData, extEventData):
        channelCnt = len(channelHeader)
        frameCnt = data.shape[0]
        self.fs = fs
        xLabel = "time [s]"

        durationSec = frameCnt / fs
        xData = np.arange(0.0, durationSec, 1.0 / fs)

        plt.ioff()

        self.fig, self.axArr = plt.subplots(channelCnt + 1, 1, sharex=True)
        try:
            self.fig.canvas.manager.set_window_title(windowName)
        except Exception:
            pass

        for i in range(channelCnt):
            self.axArr[i].plot(xData, data[:, i])
            self.axArr[i].set_ylabel(channelHeader[i])
            self.axVLines.append(
                self.axArr[i].axvline(self.vLineX, color="g", linestyle="dashed")
            )

        self._drawEvents(serialEventData, "b")
        self._drawEvents(extEventData, "k")
        self.axVLines.append(
            self.axArr[-1].axvline(self.vLineX, color="g", linestyle="dashed")
        )
        self.axArr[-1].set_ylabel("Experiment\nEvents")

        plt.xlabel(xLabel)
        plt.tight_layout()
        plt.xlim(0, xData[-1])

        plt.connect("button_press_event", self.onMouseClick)

    def _drawEvents(self, eventData, color="k"):
        vlineYtop = 1.0
        textPosY = vlineYtop + 0.2
        eventTimeList = []
        for ev in eventData:
            ev_time = ev[0] / self.fs
            eventTimeList.append(ev_time)
            self.axArr[-1].text(
                ev_time,
                textPosY,
                _field_as_str(ev[1]),
                rotation=70,
                rotation_mode="anchor",
                color=color,
                horizontalalignment="left",
                verticalalignment="center",
                clip_on=True,
            )

        self.axArr[-1].vlines(eventTimeList, 0.0, vlineYtop, colors=color, linewidths=2)
        self.axArr[-1].set_ylim((0.0, 4.0))

    def show(self):
        plt.show()


def _plotProcessFnc(
    windowName, pluxChannelHeader, fs, bioData, serialEventData, extEventData
):
    rawPlot = BioLinkRawDataPlot(
        windowName, pluxChannelHeader, fs, bioData, serialEventData, extEventData
    )
    rawPlot.show()


def plotBioLinkData(targetBaseName):
    global plotProc

    success = True

    try:
        data = np.load(targetBaseName + ".npz")
        bioData = data["bioData"]
        serialEventData = data["serialEventData"]
        extEventData = data["extensionEventData"]
        channelHeader = data["channelHeader"]
    except Exception as e:
        MsgLogger.append("Error opening '.npz' file: " + str(e))
        success = False

    try:
        with open(targetBaseName + ".json", "r") as f:
            headerDict = json.load(f)
            if "fs" in headerDict:
                fs = headerDict["fs"]
            else:
                success = False
                MsgLogger.append("Error reading fs from '.json' file.")
    except Exception as e:
        MsgLogger.append("Error opening '.json' file: " + str(e))
        success = False

    if success:
        windowName = os.path.basename(targetBaseName) + ".npz"
        plotProc = mp.Process(
            target=_plotProcessFnc,
            args=(
                windowName,
                channelHeader,
                fs,
                bioData,
                serialEventData,
                extEventData,
            ),
        )
        plotProc.daemon = True
        plotProc.start()


def terminatePlotProcess():
    global plotProc
    if plotProc:
        plotProc.terminate()


def exportTxt(targetBaseName, destinationName):
    data = np.load(targetBaseName + ".npz")
    bioData = data["bioData"]
    serialEventData = data["serialEventData"]
    extEventData = data["extensionEventData"]
    channelHeader = data["channelHeader"]

    totalFrameCnt = bioData.shape[0]
    totalSerialEventCnt = serialEventData.shape[0]
    totalExtEventCnt = extEventData.shape[0]

    exportTxt.header = ""

    def appendHeaderLine(line):
        exportTxt.header = exportTxt.header + "# " + line + os.linesep

    try:
        with open(targetBaseName + ".json", "r") as f:
            headerDict = json.load(f)
            if "version" in headerDict:
                appendHeaderLine(str(headerDict["version"]))
            if "dateStr" in headerDict:
                appendHeaderLine("Date: " + str(headerDict["dateStr"]))
            if "experimentId" in headerDict:
                appendHeaderLine("Experiment ID: " + str(headerDict["experimentId"]))
            if "subjectId" in headerDict:
                appendHeaderLine("Subject ID: " + str(headerDict["subjectId"]))
            if "duration_sec" in headerDict:
                appendHeaderLine("Duration [sec]: " + str(headerDict["duration_sec"]))
            if "frameCnt" in headerDict:
                appendHeaderLine("Total data frames: " + str(headerDict["frameCnt"]))
            if "extension" in headerDict:
                appendHeaderLine("Extension: " + str(headerDict["extension"]))
            appendHeaderLine("----------------------------------")
            if "fs" in headerDict:
                appendHeaderLine("SampleRate: " + str(headerDict["fs"]))
            if "pluxMac" in headerDict:
                appendHeaderLine("Plux Device MAC: " + str(headerDict["pluxMac"]))
    except Exception as e:
        MsgLogger.append("Error opening '.json' file: " + str(e))

    appendHeaderLine("Columns:")

    columnHdr = ""
    for h in channelHeader:
        columnHdr = columnHdr + "\t" + _field_as_str(h)
    columnHdr = columnHdr + "\tSerialEvent" + "\tExtensionEvent"
    appendHeaderLine(columnHdr)

    with open(destinationName, "w", newline="", encoding="utf-8") as f:
        f.write(exportTxt.header)
        csvWriter = csv.writer(f, delimiter="\t")

        serialEventIndex = 0
        extEventIndex = 0

        for i in range(totalFrameCnt):
            logRow = [i] + bioData[i].tolist()

            serEventStr = ""
            while (
                serialEventIndex < totalSerialEventCnt
                and serialEventData[serialEventIndex][0] == i
            ):
                if serEventStr != "":
                    serEventStr = serEventStr + ";"
                serEventStr = serEventStr + _field_as_str(
                    serialEventData[serialEventIndex][1]
                )
                serialEventIndex += 1

            if serEventStr != "":
                logRow.append(serEventStr.replace(" ", "_"))
            else:
                logRow.append("-")

            extEventStr = ""
            while extEventIndex < totalExtEventCnt and extEventData[extEventIndex][0] == i:
                if extEventStr != "":
                    extEventStr = extEventStr + ";"
                extEventStr = extEventStr + _field_as_str(extEventData[extEventIndex][1])
                extEventIndex += 1

            if extEventStr != "":
                logRow.append(extEventStr.replace(" ", "_"))
            else:
                logRow.append("-")

            csvWriter.writerow(logRow)

        if serialEventIndex != serialEventData.shape[0]:
            MsgLogger.append(
                "Some events occured after the latest sample in the data set.: "
                + str(serialEventData[serialEventIndex])
            )
