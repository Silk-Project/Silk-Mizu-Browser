import os
import re
from PySide6.QtCore import QUrl, Signal, QObject
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtGui import QColor
from services.constants import START_PAGE_PATH, SEARCH_ENGINE_SEARCH_QUERIES

class BetterWebEngineSignals(QObject):
    sum_selected_with_ai = Signal(str)
    sum_page_with_ai = Signal()

class BetterWebEngine(QWebEngineView):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.browser = parent
        self.user_settings = settings
        self.page_is_loading = False
        self.signals = BetterWebEngineSignals()
        self.page().setBackgroundColor(QColor("#101011"))
        self.urlChanged.connect(lambda: self.page().setBackgroundColor(QColor("#101011")))
        self.loadStarted.connect(lambda: setattr(self, "page_is_loading", True))
        self.loadFinished.connect(self.page_load_finished)

        self.init_engine()
        self.update_engine_config()

    def createWindow(self, window_type):
        if window_type == QWebEnginePage.WebWindowType.WebBrowserTab:
            self.browser.create_new_tab()
            return self.browser.web_tabs.widget(self.browser.web_tabs.count() - 1)
        return super().createWindow(window_type)
    
    def init_engine(self):
        # Check if start page exists
        start_page_url: str = self.user_settings.get("start_page_url")
        if start_page_url:
            # Check if start page is a file
            formatted_start_page = (start_page_url.strip()).split("file:///")

            if len(formatted_start_page) > 1:
                start_page_url_no_protocol = formatted_start_page[1]

                if os.path.exists(start_page_url_no_protocol):
                    self.setUrl(QUrl("file://" + start_page_url))

            elif os.path.exists(start_page_url):
                self.setUrl(QUrl("file://" + start_page_url))

            elif start_page_url.startswith("https://") or start_page_url.startswith("http://"):
                self.setUrl(start_page_url)

            else:
                self.load_page(start_page_url)

        else:
            if os.path.exists(START_PAGE_PATH):
                self.setUrl(QUrl("file://" + START_PAGE_PATH))
                
            else:
                self.load_page(SEARCH_ENGINE_SEARCH_QUERIES.get(self.user_settings["search_engine"]))
        
    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.addSeparator()

        sum_selected_with_ai_action = menu.addAction(self.tr("Summarize selected text with AI"))
        sum_selected_with_ai_action.triggered.connect(self.prepare_sum_selected_with_ai)

        sum_page_with_ai_action = menu.addAction(self.tr("Summarize page with AI"))
        sum_page_with_ai_action.triggered.connect(lambda: self.signals.sum_page_with_ai.emit())

        menu.exec(event.globalPos())

    def load_page(self, url):
        self.page_is_loading = True

        # Load URL if valid, else use the default search engine
        processed_url = QUrl.fromUserInput(url).toString()
        if self.valid_url(processed_url) or self.valid_url(url):
            self.setUrl(QUrl(processed_url))
        else:
            # Get url for search engine
            search_url = SEARCH_ENGINE_SEARCH_QUERIES.get(self.user_settings["search_engine"]) + url
            self.setUrl(QUrl(search_url))
    
    def reload_page(self):
        self.page_is_loading = True
        self.reload()
    
    def stop_page(self):
        self.page_is_loading = False
        self.stop()
    
    def page_load_finished(self):
        self.page_is_loading = False
        self.page().setBackgroundColor(QColor("#ffffff"))
    
    def valid_url(self, url):
        # Regex for standard http/https URLs and file paths
        regex = re.compile(
            r'^(?:(?:http|ftp)s?|file)://'  # file
            r'(?:'
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' # domain
                r'localhost|' # localhost
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # or ip
            r'|' # OR 
                r'/[^\s]+' # Absolute path for file:/// schemes
            r')'
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return re.match(regex, url) is not None
    
    def scale_page_up(self):
        zoom_factor = self.zoomFactor()
        self.setZoomFactor(zoom_factor + 0.1)

    def scale_page_down(self):
        zoom_factor = self.zoomFactor()
        self.setZoomFactor(zoom_factor - 0.1)

    def scale_page_reset(self):
        self.setZoomFactor(1)

    def prepare_sum_selected_with_ai(self):
        selected_text = self.selectedText().strip()
        
        if selected_text:
            self.signals.sum_selected_with_ai.emit(selected_text)
    
    def update_engine_config(self, new_settings=None):
        settings = self.settings()

        if new_settings:
            self.user_settings = new_settings
        
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, self.user_settings["javascript_enabled"])
        settings.setFontSize(QWebEngineSettings.FontSize.DefaultFontSize, self.user_settings["default_font_size"])
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, self.user_settings["scrollbars_enabled"])