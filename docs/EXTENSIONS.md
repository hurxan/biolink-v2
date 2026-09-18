# BioLink extensions guide

See also the **[BioLink User Manual](./MANUAL.md)** for installation, GUI, serial protocol, and data formats.

**Extensions** add behaviour during an experiment (UI, markers, custom protocols) while keeping **synchronization with PLUX frames**, the same way serial events from PsychoPy do.

## How it works

1. Choose an extension from the **Extension** drop-down in the main window (or leave **None**).
2. On **Start**, BioLink begins PLUX acquisition and, if selected, launches a **separate process** that runs your extension class.
3. The extension can:
   - emit **events** tagged with a **frame number** (same timeline as the `.npz` file);
   - receive **physiological samples** in real time (optional);
   - write a dedicated tab-separated **`.txt` log**;
   - print messages to the main window **console**.

Extension events are stored in `extensionEventData` inside the `.npz` and in the **ExtensionEvent** column after **Convert log to txt**.

## Bundled extensions

| Menu name | Folder | Purpose |
|-----------|--------|---------|
| **None** | — | PLUX + serial only (classic BioLink) |
| **template** | `biolink/extensions/template/` | Tutorial example (OK/Cancel dialog, live samples) |
| **marker_panel** | `biolink/extensions/marker_panel/` | **Hands-on demo**: manual marker buttons + auto every 5 s |

### Try `marker_panel` without hardware

1. Plux MAC: `dummy`
2. Extension: **marker_panel**
3. Subject ID: e.g. `test1` (not `nolog` if you want saved files)
4. **Start** → click *Stimulus*, *Response*, etc.
5. **End experiment** (in the panel or the main window **end** button)

Markers appear in the BioLink console and in the logs.

## Create a new extension

### 1. Folder layout

Each extension is a **subfolder** of `biolink/extensions/`:

```text
biolink/extensions/my_extension/
  __init__.py          # must expose extensionClass
  my_extension.py      # class extending ExtensionBase
```

**`__init__.py`:**

```python
from biolink.extensions.my_extension.my_extension import MyExtension

extensionClass = MyExtension
```

BioLink discovers folders automatically at startup (see `biolink/extensions/__init__.py`).

### 2. Minimal class (events only, no GUI)

```python
import time
from biolink.extensions.extension_base import ExtensionBase


class MyExtension(ExtensionBase):
    extensionName = "my_extension"   # name in the Extension menu
    logColumnHeader = ["frameNr", "event"]
    logAutomaticHeader = True

    def extMainLoop(self):
        # Example: one marker after 2 seconds, then wait until session ends
        time.sleep(2.0)
        fn = self.eib.putEvent("start_marker")
        self.logAppendLine([fn, "start_marker"])
        while not self.eib.requestEndExtention.is_set():
            time.sleep(0.2)
```

### 3. Class with a GUI (PySide6)

GUI extensions run in the **child process**: create a `QApplication` and run `app.exec()`, as in `template` and `marker_panel`.

Guidelines:

- Do not block for long in `onBioDataFrame` (called once per sample).
- To update the UI from `onBioDataFrame`, use `QTimer.singleShot(0, ...)` to marshal work to the Qt thread.
- When the user ends the session from the main window, BioLink sets `requestEndExtention` → implement `onExtEndRequest()` to close windows and quit `app.exec()`.

## `ExtensionBase` API

| Member | Description |
|--------|-------------|
| `extensionName` | Unique id (Extension menu) |
| `logColumnHeader` | Column names for the extension `.txt` file |
| `logAutomaticHeader` | If `True`, header is written before `extMainLoop` |
| `extMainLoop()` | **Required** — extension entry point |
| `logAppendLine(list)` | One TSV row in the extension log |
| `logHeader(extra_lines=None)` | Manual header when `logAutomaticHeader = False` |
| `startBioDataProcessing()` | Starts thread that calls `onBioDataFrame` |
| `stopBioDataProcessing()` | Stops the bio thread |
| `onBioDataFrame(frameNr, bioDataTup)` | Per-sample callback (must not block) |
| `onExtEndRequest()` | Called when the main app requests shutdown |

## Backend API (`self.eib`)

| Method | Description |
|--------|-------------|
| `putEvent(eventStr, frameNr=None)` | Queue an event. If `frameNr` is `None`, uses **current frame + 1**. Returns assigned frame or `-1` if the queue is full. |
| `endExperiment()` | Request session end (internal event with `frameNr == -1`) |
| `getCurrentFramenr()` | Last frame known to the main process (updated each sample) |
| `getBioData(block=True, timeout=10)` | Next sample `(frameNr, tuple)` or `(None, None)` |
| `setRequestBioData(True/False)` | Enable sample streaming (usually via `startBioDataProcessing`) |
| `consoleMessage(str)` | Message in the BioLink console |
| `requestEndExtention` | `multiprocessing.Event` — set when the main app ends the experiment |

### Time alignment

- Events are `(frame_nr, string)` pairs on the **same time base** as PLUX: time ≈ `frame_nr / sample_rate`.
- `putEvent` records the **target frame** at call time (lock on shared counter), so queue latency does not shift the label in time.
- Maximum extension event string length: **32 characters** (truncated like core BioLink).

## Output files

For an experiment `experimentId_subjectId_YYYYMMDD_HHMM`:

| File | Contents |
|------|----------|
| `log/<base>.npz` | `bioData`, `serialEventData`, `extensionEventData`, `channelHeader` |
| `log/<base>.json` | Metadata (fs, subject, extension, …) |
| `log/<base>_<extensionName>.txt` | Extension tab log (unless Subject ID is `nolog`) |

Export: **Tools → Convert log to txt** merges channels + SerialEvent + ExtensionEvent per frame.

## Extensions vs serial port

| | Serial (PsychoPy) | Extension |
|--|-------------------|-----------|
| Process | Main BioLink | Separate process |
| Protocol | Text + `\n`, `#END`, `#ID:…` | `putEvent("code")` |
| Typical use | Stimuli from external software | Built-in UI, custom protocols |

You can use **both** in one session (**Use Serial Port** checkbox).

## PsychoPy (quick reference)

BioLink does **not** import PsychoPy. Send strings on the serial port, e.g.:

```python
# PsychoPy (Builder code component or Coder)
serialPort.write(b"trial_start\n")
# end session
serialPort.write(b"#END\n")
# subject id at start
serialPort.write(b"#ID:VP01\n")
```

Use the same port and baud rate in BioLink (**115200** by default).

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| Extension missing from menu | Folder under `biolink/extensions/`, `extensionClass` in `__init__.py`, unique `extensionName` |
| `Error opening extension '…'` | Import error — see terminal / message log |
| Events missing from `.npz` | `putEvent` returned `-1`? Queue full — avoid thousands of events per second |
| GUI freezes | Blocking in `onBioDataFrame` or UI updates off the Qt thread |
| Test without PLUX | MAC `dummy`, Extension **marker_panel** |

## License and credits

Extensions are your Python code; if you distribute derivatives, comply with BioLink **LGPLv3**. Design based on [BioLinkJ/BioLink](https://github.com/BioLinkJ/BioLink).
