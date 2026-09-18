# -*- coding: utf-8 -*-
"""Live plot during experiment (separate process)."""

import multiprocessing as mp
import queue
import time

import numpy as np
from matplotlib import animation
from matplotlib import pyplot as plt


class PlotConfig:
    channelCnt = 1
    channelLabels = None
    xLabel = "Sample Nr"
    xRange = 1000
    yMin = -2048
    yMax = 2048
    reopenPlotOnClose = True


dataQueueBufLen = 10000
refreshRate = 10

plotCfg = None
fig = None
axArr = None
lineList = None
anim = None
dataQueue = None

queueInp = None
proc = None
isPlotOpen = mp.Event()


def _animateFnc(i):
    global fig, axArr, lineList, dataQueue, anim

    data_received = False

    try:
        (time_val, data) = dataQueue.get_nowait()
        data_received = True
        time_list = []
        channel_data_list = []
        for ch in range(plotCfg.channelCnt):
            channel_data_list.append([])

        while True:
            time_list.append(time_val)
            for ch in range(plotCfg.channelCnt):
                channel_data_list[ch].append(data[ch])
            (time_val, data) = dataQueue.get_nowait()

    except queue.Empty:
        pass

    if data_received:
        x = lineList[0].get_xdata()
        oldest_frame_nr = time_list[-1] - plotCfg.xRange
        cut_index = 0
        for x_val in x:
            if x_val < oldest_frame_nr:
                cut_index += 1
            else:
                break

        newx = np.concatenate((x[cut_index:], time_list))

        for ch in range(plotCfg.channelCnt):
            y = lineList[ch].get_ydata()
            newy = np.concatenate((y[cut_index:], channel_data_list[ch]))
            lineList[ch].set_data(newx, newy)
            x_end = newx[0] + plotCfg.xRange
            axArr[ch].set_xlim(newx[0], x_end)

    return lineList, axArr


def _init():
    global fig, axArr, lineList, anim

    plt.ioff()
    lineList = []
    initX = [0]
    initY = [0]

    fig, axArr = plt.subplots(plotCfg.channelCnt, 1, sharex=True)

    if plotCfg.channelCnt == 1:
        axArr = [axArr]

    for i in range(plotCfg.channelCnt):
        axArr[i].set_xlim((0, plotCfg.xRange))
        axArr[i].set_ylim((plotCfg.yMin, plotCfg.yMax))
        line, = axArr[i].plot(initX, initY, linewidth=1)
        lineList.append(line)
        if plotCfg.channelLabels:
            axArr[i].set_ylabel(plotCfg.channelLabels[i])

    plt.xlabel(plotCfg.xLabel)

    anim = animation.FuncAnimation(
        fig,
        _animateFnc,
        interval=(1000 / refreshRate),
        blit=False,
    )
    plt.tight_layout()


def _plotProcessFnc(queue_arg, plot_config, is_plot_open):
    global dataQueue, plotCfg
    dataQueue = queue_arg
    plotCfg = plot_config

    while True:
        _init()
        plt.show()
        if plot_config.reopenPlotOnClose and not dataQueue.empty():
            print("plot closed, reopening plot")
        else:
            is_plot_open.clear()
            break


def startPlotProcess(plot_config):
    global dataQueue, proc, isPlotOpen

    dataQueue = mp.Queue(dataQueueBufLen)
    isPlotOpen.set()
    proc = mp.Process(target=_plotProcessFnc, args=(dataQueue, plot_config, isPlotOpen))
    proc.start()


def plotDataFrame(time_val, data):
    global dataQueue, isPlotOpen
    if isPlotOpen.is_set():
        tup = (time_val, data)
        try:
            dataQueue.put_nowait(tup)
        except queue.Full:
            print("plotDataFrame: Queue full. Omiting data frame.")


def joinPlotProcess():
    global proc
    if proc:
        proc.join()


def terminatePlotProcess():
    global proc
    if proc:
        proc.terminate()
        isPlotOpen.clear()
        proc = None
