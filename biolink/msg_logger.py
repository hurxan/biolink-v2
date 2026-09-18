# -*- coding: utf-8 -*-
"""Message log: file + GUI console (thread-safe queue)."""

import queue
import threading
import time

msg_log_queue = queue.Queue()
view_append_fnc = None
logfile_path = None
msg_logger_thread = None


def msg_loop():
    global logfile_path
    with open(logfile_path, "w", encoding="ascii", errors="ignore") as log_file:
        while True:
            try:
                msg = msg_log_queue.get(True, 0.1)
            except queue.Empty:
                continue
            if isinstance(msg, str):
                msg_action(log_file, msg)
            elif isinstance(msg, int) and msg == -1:
                break
            else:
                msg_action(log_file, "MsgLog Error: invalid msg type, expected string.")


def init(path="log/MsgLog.txt"):
    global msg_logger_thread, logfile_path
    logfile_path = path
    msg_logger_thread = threading.Thread(target=msg_loop, daemon=True)
    msg_logger_thread.start()


def msg_action(log_file, msg):
    print(msg)
    log_file.write(msg + "\n")
    log_file.flush()
    if view_append_fnc:
        view_append_fnc(msg)


def append(msg):
    msg_log_queue.put(msg)


def append_date_time():
    append(time.strftime("%H:%M %d/%m/%Y"))


def close():
    append(-1)
    if msg_logger_thread:
        msg_logger_thread.join()
