# -*- coding: utf-8 -*-
"""Settings load/save (settings.json, version 0.4)."""

import json
import os

from biolink import msg_logger as MsgLogger
from biolink.constants import MAX_CHANNEL_CNT

if os.name == "nt":
    DEFAULT_SERIAL_PORT = "COM1"
else:
    DEFAULT_SERIAL_PORT = "/dev/ttyUSB0"


class SettingsModel:
    ver = "0.4"

    def __init__(self):
        self.setToDefaultValues()

    def setToDefaultValues(self):
        self.settingsDict = dict(
            serialPort=DEFAULT_SERIAL_PORT,
            pluxMac="xx:xx:xx:xx:xx:xx",
            channelNames=("ECG", "EDA", "BVP"),
            experimentId="test",
            sampleRate=1000,
            maxDuration=60,
            useSerial=True,
            useLifePlot=True,
            reopenLifePlot=True,
            extension="None",
        )

    def updateSettings(self, setDict):
        for k in setDict.keys():
            if k in self.settingsDict:
                self.settingsDict[k] = setDict[k]
            else:
                print("Key '" + k + "' unknown")

    def getChannelNamesStr(self):
        s = ""
        i = 1
        first_ch = True
        for ch in self.settingsDict["channelNames"]:
            if len(ch) > 0:
                if not first_ch:
                    s = s + ", "
                s = s + str(i) + ":" + ch
                first_ch = False
            i += 1
        return s

    def setChannelNamesStr(self, s):
        success = True
        ch_list = [""] * MAX_CHANNEL_CNT
        ch_strs = s.split(",")
        for ch in ch_strs:
            try:
                nr, name = ch.split(":")
                nr = int(nr.strip())
                if nr + 1 > MAX_CHANNEL_CNT:
                    success = False
                else:
                    name = name.strip()
                    if name == "":
                        success = False
                    else:
                        ch_list[nr - 1] = name
            except Exception:
                success = False
        for i in range(MAX_CHANNEL_CNT - 1, -1, -1):
            if ch_list[i] == "":
                ch_list.pop()
            else:
                break
        self.settingsDict["channelNames"] = tuple(ch_list)
        return success

    def setSampleRateStr(self, sample_rate_str):
        success = False
        try:
            sample_rate = int(sample_rate_str)
            if sample_rate >= 100:
                if sample_rate <= 1000:
                    if sample_rate % 100 == 0:
                        success = True
                    else:
                        sample_rate = (sample_rate + 50) // 100 * 100
                else:
                    sample_rate = 1000
            else:
                sample_rate = 100
            self.settingsDict["sampleRate"] = sample_rate
        except Exception:
            pass
        return success

    def getSampleRateStr(self):
        return str(self.settingsDict["sampleRate"])

    def setMaxDurationStr(self, max_duration_str):
        success = False
        try:
            max_dur = int(max_duration_str)
            if max_dur <= 480:
                if max_dur >= 1:
                    success = True
                else:
                    max_dur = 1
            else:
                max_dur = 480
            self.settingsDict["maxDuration"] = max_dur
        except Exception:
            pass
        return success

    def getMaxDurationStr(self):
        return str(self.settingsDict["maxDuration"])

    def dumpSettings(self, f):
        set_dict = {"ver": self.ver, "settings": self.settingsDict}
        json.dump(set_dict, f, indent=2)

    def loadSettings(self, f):
        self.setToDefaultValues()
        set_dict = json.load(f)
        if not ("ver" in set_dict and set_dict["ver"] == self.ver):
            MsgLogger.append(
                "Version in '" + f.name + "' does not match class version. Using default values."
            )
            return
        if "settings" in set_dict:
            self.updateSettings(set_dict["settings"])
        else:
            print("Key 'settings' not found. Using default values")


settingsModel = SettingsModel()
