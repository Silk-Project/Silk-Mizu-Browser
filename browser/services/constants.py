import sys
import platform
from platformdirs import user_config_dir, user_data_dir
from pathlib import Path

# Important paths
if getattr(sys, "frozen", False):
    SCRIPT_DIR = Path(sys._MEIPASS)
else:
    SCRIPT_DIR = Path(__file__).resolve().parent.parent

START_PAGE_PATH = SCRIPT_DIR / "assets" / "Silk-Start" / "start" / "v1.1.1" / "seperate" / "index.html"
LOGO_PATH = SCRIPT_DIR / "assets" / "mizu2.png"
ADDITIONAL_QSS_PATH = SCRIPT_DIR / "assets" / "style.qss"
NAVIGATION_SOUND_PATH = SCRIPT_DIR / "assets" / "sounds" / "navigation.wav"

# Metdata / Machine information
APPLICATION_NAME = "io.github.Silk-Project.Silk-Mizu-Browser"
VERSION_NUMBER = "0.4.11"
OS_TYPE = platform.system()

# User configs
CONFIG_DIR_PATH = Path(user_config_dir(APPLICATION_NAME, "Silk Project"))
CONFIG_DIR_PATH.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = CONFIG_DIR_PATH / "settings.json"
EXTENSIONS_SETTINGS_PATH = CONFIG_DIR_PATH / "extensions.json"

# Data paths
DATA_DIR = Path((user_data_dir(APPLICATION_NAME, "Silk Project")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

HISTORY_PATH = DATA_DIR / "history.json"
BOOKMARKS_PATH = DATA_DIR / "bookmarks.json"
DOWNLOAD_PATH = DATA_DIR / "Downloads"
EXTENSIONS_PATH = DATA_DIR / "extensions"

# Default user configs
DEFAULT_NAVBAR_LAYOUT_PATH = SCRIPT_DIR / "assets" / "default_configs" / "default_navbar_layout.json"

# AI related paths
AI_SYSPROMPT_PATH = SCRIPT_DIR / "assets" / "sysprompt.txt"
SUM_AI_MODEL = {"name":"lfm2.5-thinking:1.2b", "size":"700MB"}

# Language related
NAME_TO_LANGUAGE = {
    "English":"en_US",
    "Deutsch":"de_DE"
}
LANGUAGE_TO_NAME = {
    "en_US":"English",
    "de_DE":"Deutsch"
}

# Misc
SEARCH_ENGINE_SEARCH_QUERIES = {
    "Google":"https://www.google.com/search?q=",
    "DuckDuckGo":"https://duckduckgo.com/?q=",
    "Brave":"https://search.brave.com/search?q=",
    "Ecosia":"https://www.ecosia.org/search?method=index&q=",
    "Yahoo":"https://search.yahoo.com/search?p="
}