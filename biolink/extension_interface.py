# -*- coding: utf-8 -*-
"""Extension process interface (frontend / backend)."""

import ctypes
import threading
from multiprocessing import Process, Event, Queue, Value, Pipe
from queue import Empty, Full

from biolink import msg_logger as MsgLogger

try:
    from biolink import extensions

    extensionClasses = extensions.extensionClasses
except ImportError:
    extensionClasses = []
    print("Extensions module not found")

EVENT_QUEUE_IS_PIPE = False


def extProcessFnc(
    extensionClass,
    expConstants,
    _curFrameNr,
    consoleMsgQueue,
    eventQueue,
    bioDataQueue,
    requestBioData,
    requestEndExtention,
):
    backend = ExtensionInterfaceBackend(
        expConstants,
        _curFrameNr,
        consoleMsgQueue,
        eventQueue,
        bioDataQueue,
        requestBioData,
        requestEndExtention,
    )
    ext_instance = extensionClass(backend, expConstants)
    ext_instance.run()


class ExtensionInterfaceFrontend:
    def __init__(
        self,
        subjectId,
        experimentId,
        logDir,
        startTime,
        logFileNameBase,
        channelHeader,
        sampleFreq,
        nolog=False,
    ):
        self._curFrameNr = Value(ctypes.c_int64, -1)
        self.expConstants = ExperimentConstants(
            subjectId,
            experimentId,
            logDir,
            startTime,
            logFileNameBase,
            channelHeader,
            sampleFreq,
            nolog,
        )
        self.extensionClass = None
        self.consoleMsgQueue = Queue(maxsize=1000)

        if EVENT_QUEUE_IS_PIPE:
            self.eventConnFrontend, self.eventConnBackend = Pipe()
        else:
            self.eventQueue = Queue(maxsize=1000)

        self.bioDataQueue = Queue(maxsize=1000)
        self.requestBioData = Event()
        self.requestEndExtention = Event()

        self.extProcess = None
        self.consoleMsgThread = None

    def setCurrentFramenr(self, frameNr):
        self._curFrameNr.value = frameNr

    def checkEvents(self, curFrameNr):
        ev = []

        with self._curFrameNr.get_lock():
            if EVENT_QUEUE_IS_PIPE:
                if self.eventConnFrontend.poll():
                    ev.append(self.eventConnFrontend.recv())
            else:
                try:
                    while True:
                        ev.append(self.eventQueue.get(False))
                except Empty:
                    pass

            self._curFrameNr.value = curFrameNr

        return ev

    def putBioData(self, curFrameNr, bioDataTup):
        if self.requestBioData.is_set():
            try:
                self.bioDataQueue.put((curFrameNr, bioDataTup))
            except Full:
                print("ExtensionInterface.putBioData: bioDataQueue full")

    def selectExtensionByName(self, extName):
        success = False
        self.extensionClass = None

        if extName == "None":
            success = True
        else:
            for c in extensionClasses:
                if c.extensionName == extName:
                    self.extensionClass = c
                    success = True
                    break
        return success

    def extensionStart(self):
        if self.extensionClass is not None:
            if self.consoleMsgThread is None:
                self.consoleMsgThread = threading.Thread(
                    target=self._consoleMsgLoop, daemon=True
                )
                self.consoleMsgThread.start()

            self.requestEndExtention.clear()

            if EVENT_QUEUE_IS_PIPE:
                ev_queue = self.eventConnBackend
            else:
                ev_queue = self.eventQueue

            self.extProcess = Process(
                target=extProcessFnc,
                args=(
                    self.extensionClass,
                    self.expConstants,
                    self._curFrameNr,
                    self.consoleMsgQueue,
                    ev_queue,
                    self.bioDataQueue,
                    self.requestBioData,
                    self.requestEndExtention,
                ),
            )
            self.extProcess.start()

    def extensionEnd(self):
        self.requestEndExtention.set()

    def joinExtProcess(self, timeout=None):
        if self.extProcess:
            self.extProcess.join(timeout)

    def _consoleMsgLoop(self):
        while True:
            msg = self.consoleMsgQueue.get(block=True)
            MsgLogger.append(msg)


class ExtensionInterfaceBackend:
    def __init__(
        self,
        expConstants,
        _curFrameNr,
        consoleMsgQueue,
        eventQueue,
        bioDataQueue,
        requestBioData,
        requestEndExtention,
    ):
        self.expConstants = expConstants
        self._curFrameNr = _curFrameNr
        self.consoleMsgQueue = consoleMsgQueue

        if EVENT_QUEUE_IS_PIPE:
            self.eventConnBackend = eventQueue
        else:
            self.eventQueue = eventQueue

        self.bioDataQueue = bioDataQueue
        self.requestBioData = requestBioData
        self.requestEndExtention = requestEndExtention

    def getCurrentFramenr(self):
        return self._curFrameNr.value

    def putEvent(self, eventStr, frameNr=None):
        retval = -1
        with self._curFrameNr.get_lock():
            if frameNr is None:
                frameNr = self._curFrameNr.value + 1

            if EVENT_QUEUE_IS_PIPE:
                self.eventConnBackend.send((frameNr, str(eventStr)))
                retval = frameNr
            else:
                try:
                    self.eventQueue.put((frameNr, str(eventStr)), False)
                    retval = frameNr
                except Full:
                    print("ExtensionInterface.putEvent: eventQueue full")

        return retval

    def setRequestBioData(self, request):
        if request:
            self.requestBioData.set()
        else:
            self.requestBioData.clear()

    def getBioData(self, block=True, timeout=10):
        try:
            retval = self.bioDataQueue.get(block, timeout)
        except Empty:
            retval = (None, None)
        return retval

    def endExperiment(self):
        self.putEvent("", frameNr=-1)

    def consoleMessage(self, msg):
        self.consoleMsgQueue.put(msg)


class ExperimentConstants:
    def __init__(
        self,
        subjectId,
        experimentId,
        logDir,
        startTime,
        logFileNameBase,
        channelHeader,
        sampleFreq,
        nolog,
    ):
        self.subjectId = subjectId
        self.experimentId = experimentId
        self.logDir = logDir
        self.startTime = startTime
        self.logFileNameBase = logFileNameBase
        self.channelHeader = channelHeader
        self.sampleFreq = sampleFreq
        self.nolog = nolog


def enumerateExtensionNames():
    names = []
    for c in extensionClasses:
        names.append(c.extensionName)
    return names
