"""Application paths (log, settings) relative to project root."""
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = APP_ROOT / "log"
SETTINGS_FILE = APP_ROOT / "settings.json"

# Legacy layout: paths ending with slash for string concatenation
LOG_DIR_STR = str(LOG_DIR) + "/"
