# -*- coding: utf-8 -*-
"""PLUX device interface (OpenSignals plux module or dummy device)."""

import math
import os
import sys
import threading
import time

_plux = None


def _candidate_plux_paths():
    env = os.environ.get("BIOLINK_PLUX_PATH")
    if env:
        yield env
    if sys.platform == "win32":
        yield r"C:\Plux\OpenSignals (r)evolution\resources\app\code\modules\WIN32"
        yield r"C:\Plux\OpenSignals\resources\app\code\modules\WIN32"
    elif sys.platform == "darwin":
        yield "/Applications/OpenSignals (r)evolution.app/Contents/Resources/app/code/modules/MAC64"
        yield os.path.expanduser(
            "~/Applications/OpenSignals (r)evolution.app/Contents/Resources/app/code/modules/MAC64"
        )
    else:
        yield "/opt/plux/opensignals/code/modules/LINUX64"
        yield os.path.expanduser("~/plux/opensignals/code/modules/LINUX64")


def _load_plux():
    global _plux
    if _plux is not None:
        return _plux
    for path in _candidate_plux_paths():
        if path and os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)
        try:
            import plux as plux_mod

            _plux = plux_mod
            return _plux
        except ImportError:
            continue
    return None


def plux_available():
    return _load_plux() is not None


class Device:
    """PLUX MemoryDev wrapper when the plux module is available."""

    def __init__(self, addr):
        plux = _load_plux()
        if plux is None:
            raise ImportError(
                "PLUX OpenSignals Python module not found. "
                "Install OpenSignals or set BIOLINK_PLUX_PATH. Use MAC 'dummy' for testing."
            )

        class _Device(plux.MemoryDev):
            pipeConn = None
            stopRequest = threading.Event()

            def onRawFrame(self, nSeq, data):
                tup = (nSeq, data)
                if self.pipeConn:
                    self.pipeConn.send(tup)
                    if self.stopRequest.is_set():
                        return True
                    return False
                print("onRawFrame: ending because no pipe registered")
                return True

        self._inner = _Device(addr)

    @property
    def pipeConn(self):
        return self._inner.pipeConn

    @pipeConn.setter
    def pipeConn(self, value):
        self._inner.pipeConn = value

    @property
    def stopRequest(self):
        return self._inner.stopRequest

    def start(self, fs, channel_mask, bits_resolution):
        return self._inner.start(fs, channel_mask, bits_resolution)

    def loop(self):
        return self._inner.loop()

    def stop(self):
        return self._inner.stop()

    def close(self):
        return self._inner.close()

    def getProperties(self):
        return self._inner.getProperties()

    def getBatteryStr(self):
        bat = self._inner.getBattery()
        if bat == -1.0:
            return "charging"
        return "%.0f %%" % bat

    def endAquisition(self):
        self.stopRequest.set()


class DummyDevice:
    pipeConn = None
    stopRequest = threading.Event()

    def getProperties(self):
        return "Dummy device for testing."

    def start(self, fs, channelMask, bitsResolution):
        self.period = 1.0 / fs
        self.channelCnt = bin(channelMask).count("1")
        self.bitsResolution = bitsResolution
        self.sampleNr = 0
        self.dataMax = 2**self.bitsResolution - 1

    def loop(self):
        period2pi = self.period * 2 * math.pi
        dataMean = self.dataMax / 2
        dataAmplitude = self.dataMax / 2
        t_next = time.perf_counter() + self.period

        if self.pipeConn:
            while not self.stopRequest.is_set():
                time.sleep(self.period)
                while t_next < time.perf_counter():
                    data = int(
                        math.sin(self.sampleNr * period2pi) * dataAmplitude + dataMean
                    )
                    dataTup = tuple([data] * self.channelCnt)
                    tup = (self.sampleNr, dataTup)
                    self.pipeConn.send(tup)
                    self.sampleNr += 1
                    t_next += self.period
        else:
            print("DummyDevice.loop: ending because no pipe registered")

    def stop(self):
        pass

    def close(self):
        pass

    def getBatteryStr(self):
        return "150 %"

    def endAquisition(self):
        self.stopRequest.set()


def enumDevices():
    plux = _load_plux()
    if plux is None:
        raise ImportError(
            "PLUX module not available. Set BIOLINK_PLUX_PATH or use MAC address 'dummy'."
        )
    return plux.BaseDev.findDevices()


def openDevice(addr):
    if addr != "dummy":
        return Device(addr)
    return DummyDevice()
