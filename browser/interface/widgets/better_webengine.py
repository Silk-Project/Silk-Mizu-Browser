import os
import re
from PySide6.QtCore import QUrl, Signal, QObject
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtGui import QColor
from services.constants import START_PAGE_PATH, SEARCH_ENGINE_SEARCH_QUERIES
from urllib.parse import urlparse, quote_plus

class BetterWebEngineSignals(QObject):
    sum_selected_with_ai = Signal(str)
    sum_page_with_ai = Signal()
    zoom_factor_changed = Signal(float)

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
        formatted_url = self.validate_and_fix_url(url)
        self.setUrl(QUrl(formatted_url))
    
    def reload_page(self):
        self.page_is_loading = True
        self.reload()
    
    def stop_page(self):
        self.page_is_loading = False
        self.stop()
    
    def page_load_finished(self):
        self.page_is_loading = False
    
    def validate_and_fix_url(self, url_string):
        clean_input = url_string.strip()
        
        localhost_match = re.match(r'^(localhost)(?::\d+)?(?:\/.*)?$', clean_input, re.IGNORECASE)
        domain_match = re.match(r'^([a-z0-9-]+(?:\.[a-z0-9-]+)+)(?::\d+)?(?:\/.*)?$', clean_input, re.IGNORECASE)
        
        # Add scheme if it's missing
        if (domain_match or localhost_match) and not clean_input.startswith(('http://', 'https://', 'file://', 'ftp://')):
            clean_input = "http://" + clean_input

        try:
            result = urlparse(clean_input)
            
            # Validate Web URLs
            if result.scheme in ['http', 'https']:
                if result.netloc:
                    return clean_input
                    
            # Validate Local File URLs
            elif result.scheme == 'file':
                if result.path:
                    return clean_input
                    
            # Validate other explicit schemes
            elif result.scheme and result.netloc:
                return clean_input

        except Exception:
            pass

        search_url = SEARCH_ENGINE_SEARCH_QUERIES.get(self.user_settings["search_engine"]) + quote_plus(url_string)
        return search_url
    
    def scale_page_up(self):
        zoom_factor = self.zoomFactor()
        self.setZoomFactor(zoom_factor + 0.1)
        self.signals.zoom_factor_changed.emit(self.zoomFactor())

    def scale_page_down(self):
        zoom_factor = self.zoomFactor()
        self.setZoomFactor(zoom_factor - 0.1)
        self.signals.zoom_factor_changed.emit(self.zoomFactor())

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