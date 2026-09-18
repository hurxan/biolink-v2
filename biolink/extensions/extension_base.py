# -*- coding: utf-8 -*-
"""Base class for BioLink extensions."""

import csv
import threading
import time


class ExtensionBase:
    logColumnHeader = []
    logAutomaticHeader = True
    extensionName = "base"

    def __init__(self, extensionInterfaceBackend, extConstnats):
        self.eib = extensionInterfaceBackend
        self.extConstants = extConstnats
        self.logfile = None
        self.logCsvWriter = None
        self.dataProcessingEndRequest = threading.Event()
        self.dataProcessingThread = None
        self.mainTrheadRunning = threading.Event()

    def _requestEndExtentionLoop(self):
        while self.mainTrheadRunning.is_set():
            if self.eib.requestEndExtention.wait(1):
                self.onExtEndRequest()
                break

    def run(self):
        self.mainTrheadRunning.set()
        endExtentionThread = threading.Thread(
            target=self._requestEndExtentionLoop, daemon=True
        )
        endExtentionThread.start()

        self._logOpen()
        if self.logAutomaticHeader:
            self.logHeader()

        try:
            self.extMainLoop()
        except Exception as e:
            self.eib.consoleMessage(
                self.extensionName + ": Exception in extMainLoop: " + str(e)
            )

        self._logClose()
        self.mainTrheadRunning.clear()
        endExtentionThread.join(10)

    def extMainLoop(self):
        print("extMainLoop: Please override method in your extension class.")

    def _logOpen(self):
        if not self.extConstants.nolog:
            fileName = (
                self.extConstants.logDir
                + self.extConstants.logFileNameBase
                + "_"
                + self.extensionName
                + ".txt"
            )
            try:
                self.logfile = open(fileName, "w", newline="")
                self.logCsvWriter = csv.writer(self.logfile, delimiter="\t")
            except Exception:
                self.eib.consoleMessage("Error creating logfile: '" + fileName + "'")
                self.logfile = None
        else:
            self.logfile = None

    def logHeader(self, extensionHeaderLines=None):
        def logWriteHdrLine(line):
            self.logfile.write("# " + line + "\r\n")

        if self.logfile:
            logWriteHdrLine("BioLink extension " + self.extensionName)
            logWriteHdrLine(
                "Date: "
                + time.strftime("%d/%m/%Y %H:%M", self.extConstants.startTime)
            )
            logWriteHdrLine("Experiment ID: " + self.extConstants.experimentId)
            logWriteHdrLine("Subject ID: " + self.extConstants.subjectId)
            if extensionHeaderLines is not None:
                logWriteHdrLine("----------------------------------")
                for line in extensionHeaderLines:
                    logWriteHdrLine(line)
            logWriteHdrLine("----------------------------------")
            logWriteHdrLine("Columns:")
            columnHdr = ""
            for h in self.logColumnHeader:
                columnHdr = columnHdr + h + "\t"
            columnHdr = columnHdr[:-1]
            logWriteHdrLine(columnHdr)
        else:
            print("logHeader: no logfile open")

    def logAppendLine(self, dataList):
        if self.logfile:
            if len(dataList) > len(self.logColumnHeader):
                print("logAppendLine: dataList longer than column count.")
                dataList = dataList[: len(self.logColumnHeader)]
            self.logCsvWriter.writerow(dataList)

    def _logClose(self):
        if self.logfile:
            self.logfile.close()
            self.logfile = None
            self.logCsvWriter = None

    def _bioDataProcessingLoop(self):
        while not self.dataProcessingEndRequest.is_set():
            frameNr, bioDataTup = self.eib.getBioData(block=True, timeout=10)
            if frameNr is not None:
                self.onBioDataFrame(frameNr, bioDataTup)
            else:
                if not self.dataProcessingEndRequest.is_set():
                    print("ExtensionBase._bioDataProcessingLoop: no data")

    def startBioDataProcessing(self):
        self.eib.setRequestBioData(True)
        self.dataProcessingEndRequest.clear()
        self.dataProcessingThread = threading.Thread(
            target=self._bioDataProcessingLoop, daemon=True
        )
        self.dataProcessingThread.start()

    def stopBioDataProcessing(self):
        self.eib.setRequestBioData(False)
        self.dataProcessingEndRequest.set()

    def onBioDataFrame(self, frameNr, bioDataTup):
        print("onBioDataFrame: Please override method in your extension class.")

    def onExtEndRequest(self):
        print("onExtEndRequest: Please override method in your extension class.")
