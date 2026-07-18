import os
import platform

# Important paths
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START_PAGE_PATH = os.path.join(SCRIPT_DIR, "assets", "Silk-Start", "start", "v1.1.1", "seperate", "index.html")
LOGO_PATH = os.path.join(SCRIPT_DIR, "assets", "mizu2.png")
ADDITIONAL_QSS_PATH = os.path.join(SCRIPT_DIR, "assets", "style.qss")
NAVIGATION_SOUND_PATH = os.path.join(SCRIPT_DIR, "assets", "sounds", "navigation.wav")

# Metdata / Machine information
VERSION_NUMBER = "0.4.0"
OS_TYPE = platform.system()

# User configs
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config", "settings.json")
BOOKMARKS_PATH = os.path.join(SCRIPT_DIR, "config", "bookmarks.json")
EXTENSIONS_SETTINGS_PATH = os.path.join(SCRIPT_DIR, "config", "extensions.json")
HISTORY_PATH = os.path.join(SCRIPT_DIR, "config", "history.json")

# User directories
DOWNLOAD_PATH = os.path.join(SCRIPT_DIR, "Downloads")
EXTENSIONS_PATH = os.path.join(SCRIPT_DIR, "extensions")

# Default user configs
DEFAULT_NAVBAR_LAYOUT_PATH = os.path.join(SCRIPT_DIR, "interface", "navigation", "default_navbar_layout.json")

# AI related paths
AI_SYSPROMPT_PATH = os.path.join(SCRIPT_DIR, "config", "sysprompt.txt")
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