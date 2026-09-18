# BioLink

<div align="center">

**BioLink** — synchronized psycho-physiological and behavioural data acquisition (PLUX + stimulus events, e.g. from PsychoPy via serial).

**[User manual](./docs/MANUAL.md)** · LGPLv3

</div>

## About

BioLink acquires physiological data from **PLUX Biosignals** devices and aligns **stimulus/event markers** (typically sent over a **serial port** from PsychoPy or similar) on a **single timeline**. Recordings are saved as `.npz` + `.json` and can be exported to tab-separated `.txt`.

Cross-platform desktop app: **Windows**, **macOS**, and **Linux**.

## Requirements

- **Python 3.10+**
- Dependencies in `requirements.txt` (PySide6, numpy, matplotlib, pyserial)
- **PLUX**: OpenSignals with the Python `plux` module, or MAC address **`dummy`** for testing without hardware

## Install & run

```sh
git clone git@github.com:hurxan/biolink-v2.git
cd biolink-v2
pip install -r requirements.txt
python -m biolink
```

- **macOS / Linux:** `./run.sh`
- **Windows:** double-click `start.bat` or `python -m biolink`

Settings are stored in `settings.json` (project root). Logs go to `log/`.

### PLUX hardware

1. Pair the device (USB dongle or Bluetooth, PIN often `123`).
2. Install **OpenSignals (r)evolution** so the Python `plux` module is available.
3. If BioLink does not find it automatically, set **`BIOLINK_PLUX_PATH`** to the directory that contains `plux` (e.g. OpenSignals `.../code/modules/WIN32` or `MAC64`).

Use **find devices** in the app or enter the MAC address manually. For offline development, set Plux MAC to **`dummy`**.

### Extensions

Custom extensions live under `biolink/extensions/<name>/`. Included demos:

- **`template`** — minimal dialog + live samples (learning)
- **`marker_panel`** — manual/auto markers for testing without PsychoPy or serial

**Extensions guide:** [docs/EXTENSIONS.md](./docs/EXTENSIONS.md)

## Usage

See the **[complete user manual](./docs/MANUAL.md)** (installation, GUI, PLUX, serial/PsychoPy, data formats, troubleshooting).

Quick tips:

- Subject ID **`nolog`**: run without saving `.npz`/`.json`
- Serial events: lines terminated with `\n`; **`#END`** stops the session; **`#ID:…`** can supply Subject ID
- **Tools → Convert log to txt** / **Plot BioLink Data**

## Built with

- Python 3, [PySide6](https://wiki.qt.io/Qt_for_Python)
- numpy, matplotlib, pyserial

## Legacy (BioLink 1.x)

Documentation for the retired Python 2 / GTK application is archived separately:

- **[docs/legacy/](./docs/legacy/)** — index  
- **[Manual.pdf](./docs/legacy/Manual.pdf)** — original 1.x user manual (reference; UI and install steps differ from BioLink 2)

## Acknowledgments

- [Original BioLink / BioLinkJ](https://github.com/BioLinkJ/BioLink) (University Hospital Zurich)
- Community forks and contributors
