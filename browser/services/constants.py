import os
import platform

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config", "settings.json")
BOOKMARKS_PATH = os.path.join(SCRIPT_DIR, "config", "bookmarks.json")
LOGO_PATH = os.path.join(SCRIPT_DIR, "assets", "mizu2.png")
START_PAGE_PATH = os.path.join(SCRIPT_DIR, "assets", "Silk-Start", "start", "v1.1.1", "seperate", "index.html")
AI_SYSPROMPT_PATH = os.path.join(SCRIPT_DIR, "config", "sysprompt.txt")
DOWNLOAD_PATH = os.path.join(SCRIPT_DIR, "Downloads")
EXTENSIONS_PATH = os.path.join(SCRIPT_DIR, "extensions")
EXTENSIONS_SETTINGS_PATH = os.path.join(SCRIPT_DIR, "config", "extensions.json")
ADDITIONAL_QSS_PATH = os.path.join(SCRIPT_DIR, "assets", "style.qss")
DEFAULT_NAVBAR_LAYOUT_PATH = os.path.join(SCRIPT_DIR, "interface", "navigation", "default_navbar_layout.json")
SUM_AI_MODEL = {"name":"lfm2.5-thinking:1.2b", "size":"700MB"}
VERSION_NUMBER = "0.4.0 Beta"
OS_TYPE = platform.system()
SEARCH_ENGINE_SEARCH_QUERIES = {
    "Google":"https://www.google.com/search?q=",
    "DuckDuckGo":"https://duckduckgo.com/?q=",
    "Brave":"https://search.brave.com/search?q=",
    "Ecosia":"https://www.ecosia.org/search?method=index&q=",
    "Yahoo":"https://search.yahoo.com/search?p="
}
NAME_TO_LANGUAGE = {
    "English":"en_US",
    "Deutsch":"de_DE"
}
LANGUAGE_TO_NAME = {
    "en_US":"English",
    "de_DE":"Deutsch"
}
