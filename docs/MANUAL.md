# BioLink User Manual

**Version:** BioLink 2.x (Python 3)  
**Document:** complete user and operator guide  
**License:** LGPLv3 (see [LICENSE](../LICENSE))

---

## Table of contents

1. [Introduction](#1-introduction)
2. [What BioLink does](#2-what-biolink-does)
3. [Requirements](#3-requirements)
4. [Installation](#4-installation)
5. [Starting BioLink](#5-starting-biolink)
6. [Main window](#6-main-window)
7. [Settings reference](#7-settings-reference)
8. [Running an experiment](#8-running-an-experiment)
9. [PLUX devices](#9-plux-devices)
10. [Serial port and PsychoPy](#10-serial-port-and-psychopy)
11. [Live plot](#11-live-plot)
12. [Extensions](#12-extensions)
13. [Ending a session](#13-ending-a-session)
14. [Recorded data and file formats](#14-recorded-data-and-file-formats)
15. [Tools menu](#15-tools-menu)
16. [Settings file (`settings.json`)](#16-settings-file-settingsjson)
17. [Message log and console](#17-message-log-and-console)
18. [Workflow examples](#18-workflow-examples)
19. [Troubleshooting](#19-troubleshooting)
20. [Credits and further reading](#20-credits-and-further-reading)

---

## 1. Introduction

BioLink is a desktop application for **research-grade synchronized recording** of:

- **Physiological signals** from PLUX Biosignals hardware (via OpenSignals), and  
- **Event markers** from behavioural software (typically **PsychoPy** over a **serial port**) or from **BioLink extensions**.

All samples and events share one **frame-based timeline** tied to the PLUX sample clock. Data are stored in open formats (NumPy `.npz`, JSON metadata, optional tab-separated export) for analysis in MATLAB, Python, R, or other tools.

BioLink 2 runs on **Windows**, **macOS**, and **Linux** using **Python 3.10+** and a **PySide6** graphical interface.

> **Note:** Legacy BioLink 1.x documentation (Python 2 / GTK) is in **[docs/legacy/](./legacy/)**. Serial protocol and file semantics largely match BioLink 2; **this manual** is the authoritative guide for the current application.

---

## 2. What BioLink does

During a session BioLink:

1. Opens a PLUX device (or a **dummy** generator for testing).
2. Streams multi-channel data at a configured sample rate (default **1000 Hz**).
3. Listens for **serial events** (if enabled) and/or runs an **extension** (optional).
4. Assigns each event a **frame number** matching the physiological data.
5. Optionally shows a **live matplotlib plot**.
6. On stop, saves compressed **`.npz`** data plus **`.json`** metadata under `log/`.

**Frame time:**  
\(\text{time [s]} = \text{frame\_nr} / \text{sample\_rate}\)

Example at 1000 Hz: frame `15000` → 15.000 s from session start.

---

## 3. Requirements

### Software

| Component | Version / notes |
|-----------|-----------------|
| Python | 3.10 or newer |
| BioLink dependencies | See [requirements.txt](../requirements.txt): PySide6, numpy, matplotlib, pyserial |
| OpenSignals (PLUX) | Required for **real** hardware; provides the Python `plux` module |
| PsychoPy or other | Optional; sends markers over serial |

### Hardware

- PLUX Biosignals kit (e.g. Bitalino / PLUX hub + sensors), **or** use **`dummy`** for software-only tests.
- USB serial adapter or built-in COM port if using serial markers.
- Display recommended if using live plot or extension GUIs.

### Permissions

- **Serial ports:** user must be allowed to open the port (on Linux, user in `dialout` group may be required).
- **Bluetooth PLUX:** pair device in the OS; default PIN is often **123** (see PLUX documentation).

---

## 4. Installation

### 4.1 Get the project

Clone or unpack the BioLink repository into a folder, e.g. `biolink-master`.

### 4.2 Create an environment (recommended)

```sh
cd biolink-master
python3 -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

Or install as a package:

```sh
pip install -e .
```

### 4.3 PLUX / OpenSignals (real hardware)

1. Install **OpenSignals (r)evolution** from PLUX.
2. Ensure the Python **`plux`** module is available (shipped with OpenSignals, platform-specific folder).
3. If BioLink cannot find it, set environment variable **`BIOLINK_PLUX_PATH`** to the directory containing `plux` (see [§9](#9-plux-devices)).

### 4.4 Directories created at runtime

| Path | Purpose |
|------|---------|
| `log/` | Session data (`.npz`, `.json`, message logs, extension logs) |
| `settings.json` | Last-used GUI settings (project root) |

---

## 5. Starting BioLink

| Platform | Command |
|----------|---------|
| Any | `python -m biolink` |
| macOS / Linux | `./run.sh` |
| Windows | Double-click `start.bat` or `python -m biolink` |

On first start, settings load from `settings.json` if present; otherwise defaults apply.

Close the window only after **ending** an active experiment (see [§13](#13-ending-a-session)); BioLink warns you if a session is still running.

---

## 6. Main window

The window has three areas: **menu bar**, **Settings**, **Experiment**, and **Messages**.

### Menu bar

| Menu | Item | Action |
|------|------|--------|
| **Tools** | Convert log to txt | Export a saved `.npz` session to a human-readable `.txt` table |
| **Tools** | Plot BioLink Data | Open an offline review plot for a saved `.npz` |
| **Settings** | Default Values | Reset all settings fields to factory defaults (does not delete log files) |

### Settings group

Fields used for every new session (frozen while an experiment runs).

### Experiment group

**Experiment ID**, **Subject ID**, and **start** / **end** buttons.

### Messages

Scrollable console: serial events, PLUX status, extension messages, errors, and save confirmations. A separate **message log file** is also written under `log/` (see [§17](#17-message-log-and-console)).

---

## 7. Settings reference

### Serial Port

- **Windows:** e.g. `COM3`, `COM4`
- **macOS:** e.g. `/dev/cu.usbserial-*`
- **Linux:** e.g. `/dev/ttyUSB0`, `/dev/ttyACM0`

Use **find ports** to list detected ports in the Messages area.

**Use Serial Port:** if unchecked, BioLink does not open the serial port during a session (extension-only or PLUX-only recording).

Default baud rate is **115200** (fixed in software; not exposed in GUI).

### Plux MAC

Bluetooth or device address in form `xx:xx:xx:xx:xx:xx`.

| Value | Meaning |
|-------|---------|
| Real MAC | Connect to PLUX via OpenSignals `plux` module |
| **`dummy`** | Simulated sine-wave data on all active channels (no hardware) |

Use **find devices** to scan (requires working `plux` module). Close any live plot before scanning if devices fail to appear.

**Tooltips:** Subject ID `nolog` disables file save; Plux MAC `dummy` enables test mode.

### Channel Names

Defines which PLUX **physical channels** are active and their labels in logs.

- Format: comma-separated **`index:name`** pairs, e.g. `1:ECG, 2:EDA, 3:BVP`
- Index **1** = first PLUX channel, up to **8** channels maximum
- Empty slots at the end are trimmed; invalid format blocks **Start**

Only named channels are enabled in the **channel mask** (bit mask sent to the device).

### Sample Rate [Hz]

- Allowed range after validation: **100–1000 Hz**
- Must be a **multiple of 100** (values are rounded to nearest 100 Hz if needed)
- Default: **1000**

Must be set before **Max Duration** is applied internally (duration in frames = minutes × 60 × fs).

### Max Duration [min]

- Minimum **1** minute, maximum **480** minutes (8 hours)
- Default: **60**
- When reached, acquisition stops automatically and data are saved

### Life Plot

| Option | Effect |
|--------|--------|
| **Paint Life Plot** | Opens a separate matplotlib window updating during the session |
| **Reopen Life Plot if closed** | If you close the plot window while data remain in the buffer, BioLink opens a new plot window |

Live plot shows the last **10 seconds** of data per channel (time axis in seconds).

### Extension

Drop-down of discovered extensions under `biolink/extensions/` plus **None**.

- **None:** no extension process
- **template:** tutorial dialog (see [Extensions guide](./EXTENSIONS.md))
- **marker_panel:** manual marker buttons for testing without PsychoPy

---

## 8. Running an experiment

### 8.1 Checklist before Start

1. Configure **Settings** (PLUX MAC, channels, rate, serial port if used).
2. Enter **Experiment ID** (used in filenames).
3. Enter **Subject ID** *or* plan to receive it via serial `#ID:…` *or* use **`nolog`** for a dry run without saving.
4. Select **Extension** if needed.
5. Attach sensors / pair PLUX / connect serial from PsychoPy machine.

### 8.2 Start sequence (what happens internally)

When you click **start**:

1. Settings are validated and written to `settings.json`.
2. BioLink opens the PLUX device (may take several seconds).
3. On Windows, **sleep prevention** is enabled for the session.
4. If **Use Serial Port** is on, the serial port is opened (failure is logged but may not abort if Subject ID was typed).
5. If Subject ID is empty and serial is open, a dialog waits for `#ID:…` (cancel → abort).
6. If Subject ID is set, UI settings are frozen, **start** disabled, **end** enabled.
7. PLUX acquisition thread and logging thread start; extension process starts if selected; live plot may start; serial **reconnect** thread runs if serial is enabled.

### 8.3 During acquisition

- Each PLUX frame: data stored, serial/extension events checked, optional plot update.
- Serial disconnect: `#noconn` event logged; reconnect attempts every second; on reconnect `#reconn` is logged.
- Extension and serial events appear in Messages with frame numbers.

### 8.4 Subject ID special values

| Subject ID | Behaviour |
|------------|-----------|
| Normal text (e.g. `VP01`) | Saves `log/<experimentId>_<subjectId>_<timestamp>.npz` and `.json` |
| **`nolog`** | Runs acquisition and UI normally but **does not write** `.npz`/`.json` (extension may still skip its own log) |

---

## 9. PLUX devices

### 9.1 Dummy mode (no hardware)

Set **Plux MAC** to `dummy`. BioLink generates synthetic 16-bit samples on all configured channels. Use this to:

- Test serial or extensions  
- Train operators  
- Develop analysis pipelines  

### 9.2 Real device

1. Pair PLUX in the operating system (USB dongle or Bluetooth).
2. Install OpenSignals so **`plux`** imports successfully.
3. Enter MAC or use **find devices**.
4. Battery status is printed to Messages at open and close.

### 9.3 `BIOLINK_PLUX_PATH`

If auto-detection fails, set this environment variable to the folder that contains the `plux` Python extension, for example:

| OS | Typical path (varies by install) |
|----|----------------------------------|
| Windows | `C:\Plux\OpenSignals (r)evolution\resources\app\code\modules\WIN32` |
| macOS | `.../OpenSignals (r)evolution.app/Contents/Resources/app/code/modules/MAC64` |
| Linux | `.../opensignals/.../LINUX64` |

Restart BioLink after changing the variable.

### 9.4 Resolution and channels

- Samples are **16-bit** unsigned integers in saved arrays.
- Channel count equals the number of names in **Channel Names** (up to 8).

---

## 10. Serial port and PsychoPy

BioLink does **not** embed PsychoPy. PsychoPy (or any program) sends **UTF-8/Latin-1 compatible text lines** terminated by **newline** (`\n`).

### 10.1 Event format

- General marker: any string + `\n`, e.g. `trial_start\n`
- Maximum effective length **16 characters** per serial event (longer strings truncated)

### 10.2 Special commands

| Sent on serial | BioLink action |
|----------------|----------------|
| `#END\n` | Ends experiment cleanly (same as clicking **end**) |
| `#ID:SubjectName\n` | Supplies Subject ID when the main field was left empty at Start |

### 10.3 Connection events (generated by BioLink)

| Tag | Meaning |
|-----|---------|
| `#noconn` | Serial read failed / device unplugged |
| `#reconn` | Serial port opened again after disconnect |

### 10.4 PsychoPy example (Coder)

```python
from psychopy.hardware.serialport import SerialPort

port = SerialPort(name="COM3")  # match BioLink Serial Port

port.write(b"trial_start\n")
# ...
port.write(b"#END\n")
```

Use the same port name and **115200** baud as BioLink. In Builder, use a Code component with the same byte strings.

### 10.5 Subject ID over serial at Start

If **Subject ID** is empty but serial is connected, BioLink shows a waiting dialog. PsychoPy (or a small script) should send:

```text
#ID:VP01\n
```

Cancel the dialog to abort Start.

---

## 11. Live plot

- Separate **matplotlib** process (not embedded in main window).
- Shows last **10 s** per channel; Y range **0 … 65535** (16-bit).
- X axis: **Seconds** from session start.
- Closing the plot: if **Reopen Life Plot if closed** is enabled and buffered data remain, a new window opens.

**Tip:** Close the live plot before **find devices** or reopening PLUX if you see device lock issues.

---

## 12. Extensions

Extensions run in a **child process** and send events through the same frame timeline as serial markers.

Bundled extensions:

| Name | Purpose |
|------|---------|
| `template` | Learning example: dialog + live bio display |
| `marker_panel` | Button panel for manual / auto markers without serial |

For development API, file layout, and examples, see **[Extensions guide](./EXTENSIONS.md)**.

Extension events:

- Stored in `extensionEventData` in the `.npz`
- Max label length **32 characters**
- Frame **-1** is internal end request (handled by core; not stored as user event)

Extension log file (when not `nolog`):

```text
log/<base>_<extensionName>.txt
```

Tab-separated with `#` comment header (same style as exported main log).

---

## 13. Ending a session

Ways to stop:

| Method | Notes |
|--------|-------|
| Click **end** in main window | Preferred; waits up to ~11 s for clean shutdown, then may force-save |
| Serial `#END\n` | Same as **end** |
| Extension `endExperiment()` | e.g. marker panel **End experiment** |
| **Max Duration** elapsed | Automatic stop and save |
| Close main window | Blocked while experiment running |

On stop:

1. PLUX loop stops, data flushed to `.npz`/`.json` (unless `nolog`).
2. Extension asked to stop; serial closed; live plot terminated.
3. Subject ID field cleared; settings unfrozen; sleep prevention released (Windows).

**Forced save:** If shutdown hangs, after **11 seconds** BioLink may save with suffix `_forcedsave` in the filename.

---

## 14. Recorded data and file formats

### 14.1 Filename pattern

```text
log/<experimentId>_<subjectId>_<YYYYMMDD>_<HHMM>
```

Extensions add:

```text
log/<experimentId>_<subjectId>_<YYYYMMDD>_<HHMM>_<extensionName>.txt
```

### 14.2 JSON sidecar (`.json`)

Example fields:

| Field | Description |
|-------|-------------|
| `version` | BioLink version string |
| `dateStr` | Local start time `dd/mm/YYYY HH:MM` |
| `experimentId`, `subjectId` | From GUI |
| `fs` | Sample rate |
| `frameCnt` | Number of frames saved |
| `duration_sec` | `frameCnt / fs` |
| `channels` | List of channel names |
| `pluxMac` | Device MAC or `dummy` |
| `extension` | Extension name or `None` |

### 14.3 NumPy archive (`.npz`)

| Array | Description |
|-------|-------------|
| `bioData` | Shape `(n_frames, n_channels)`, `uint16` |
| `channelHeader` | Channel name strings |
| `serialEventData` | Structured: `frame_nr` (uint32), `event_str` (S16) |
| `extensionEventData` | Structured: `frame_nr` (uint32), `event_str` (S32) |

Load in Python:

```python
import numpy as np
d = np.load("log/test_VP01_20260918_1200.npz")
bio = d["bioData"]
events = d["serialEventData"]
```

### 14.4 Exported text (Tools → Convert log to txt)

- Header lines start with `#`
- Data rows: tab-separated  
  `frame_index`, channel values…, `SerialEvent`, `ExtensionEvent`
- Missing event: `-`
- Multiple events same frame: joined with `;`
- Spaces in event strings replaced by `_` in export

First column is **frame index** (0-based), aligned with rows in `bioData`.

---

## 15. Tools menu

### Convert log to txt

1. Choose `.npz` (same basename as `.json`).
2. Choose output `.txt` path.
3. Conversion runs in background; completion message appears in Messages.

### Plot BioLink Data

1. Choose `.npz`.
2. Offline matplotlib window: all channels vs time + event lane (serial blue, extension black).
3. Click plot to move a vertical cursor across subplots.

---

## 16. Settings file (`settings.json`)

Location: project root. Schema version **`0.4`**.

```json
{
  "ver": "0.4",
  "settings": {
    "serialPort": "COM1",
    "pluxMac": "xx:xx:xx:xx:xx:xx",
    "channelNames": ["ECG", "EDA", "BVP"],
    "experimentId": "test",
    "sampleRate": 1000,
    "maxDuration": 60,
    "useSerial": true,
    "useLifePlot": true,
    "reopenLifePlot": true,
    "extension": "None"
  }
}
```

If `ver` does not match, BioLink loads defaults and logs a warning.

Settings are saved when a session **starts successfully** and when the main window closes (if no experiment is running).

**Settings → Default Values** resets the in-memory model and GUI; save occurs on next successful Start or exit.

---

## 17. Message log and console

- **Console (GUI):** real-time operator feedback.
- **File log:** `log/BioLink_MsgLog_YYYYMMDD_HHMM.txt` created at each application launch.

Extension `consoleMessage()` output also appears in both.

---

## 18. Workflow examples

### A. Full lab session (PLUX + PsychoPy)

1. PLUX MAC = device address; channels `1:ECG, 2:EDA, 3:BVP`; serial = PsychoPy COM port.
2. PsychoPy sends `#ID:VP01\n` then trial markers; BioLink **Start** with empty Subject ID or pre-filled ID.
3. PsychoPy sends `#END\n` or operator clicks **end**.
4. **Tools → Convert log to txt** for SPSS / Excel / R.

### B. Extension-only test (no serial)

1. Plux MAC = `dummy`; uncheck **Use Serial Port**; Extension = `marker_panel`.
2. Subject ID = `test01`; **Start**; click markers; **End experiment**.
3. Inspect `.npz` in Python or offline plot.

### C. Visualization only

1. Subject ID = **`nolog`**; enable **Paint Life Plot**; dummy or real PLUX.
2. No `.npz` written; useful for checking signal quality.

---

## 19. Troubleshooting

| Symptom | Possible cause | Action |
|---------|----------------|--------|
| Error opening Plux device | Wrong MAC, OpenSignals not installed, `plux` not on path | Try `dummy`; set `BIOLINK_PLUX_PATH`; use **find devices** |
| No serial events | Wrong port, baud mismatch, cable | **find ports**; verify 115200; test with terminal |
| Invalid Channel Names | Syntax error in list | Use `1:ECG, 2:EDA` format |
| Extension not in menu | Import error in extension folder | Check Messages / terminal on startup |
| Empty Subject ID abort | No serial ID and empty field | Enter ID or send `#ID:…` |
| Plot blocks device scan | Known interaction | **end** plot / close live plot before find/open |
| Linux serial permission denied | User not in `dialout` | `sudo usermod -aG dialout $USER` and re-login |
| macOS serial port name | Use `cu.*` not only `tty.*` | Select `/dev/cu.usbserial-…` from find ports |
| Forced save file | Slow PLUX stop | Check `_forcedsave` file; data still usable |
| Queue full (extension) | Too many events/sec | Reduce event rate |

---

## 20. Credits and further reading

- **Original BioLink:** Julian Schneider, University Hospital Zurich; [BioLinkJ/BioLink](https://github.com/BioLinkJ/BioLink).
- **BioLink 2:** Python 3 / PySide6 rewrite; behaviour compatible with classic BioLink 1.4 acquisition semantics.
- **Extensions development:** [docs/EXTENSIONS.md](./EXTENSIONS.md)
- **Quick start:** [README.md](../README.md)
- **Legacy (1.x):** [docs/legacy/](./legacy/) — [Manual.pdf](./legacy/Manual.pdf)

**Disclaimer:** BioLink is research software, not a certified medical device. Verify signal quality and synchronization for your protocol before collecting participant data.

---

*End of manual.*
