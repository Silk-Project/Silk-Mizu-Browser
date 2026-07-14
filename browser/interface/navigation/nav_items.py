from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QLineEdit,
    QProgressBar
)
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from interface.widgets.better_webengine import BetterWebEngine
import qtawesome as qta

class AddressBar(QLineEdit):
    def __init__(self, controller, parent=None):
        super().__init__(parent)

        self.browser: BetterWebEngine = None

        self.setPlaceholderText("https://")

        controller.currentBrowserChanged.connect(self.set_browser)    
        self.returnPressed.connect(self.on_return_pressed)
    
    def set_browser(self, browser):
        if self.browser:
            self.browser.urlChanged.disconnect(self.update_url)

        self.browser = browser

        self.browser.urlChanged.connect(self.update_url)

        self.update_url(browser.url())

    def update_url(self, url: QUrl):
        str_url = url.toString()
        self.setText(str_url)

    def on_return_pressed(self):
        if not self.browser:
            return

        url = self.text()
        self.browser.load_page(url)

class BackBtn(QPushButton):
    def __init__(self, controller, parent = None):
        super().__init__(parent)

        self.browser: BetterWebEngine = None
        self.icon_id = "fa6s.arrow-left"
        self.icon_color = "white"

        self.setIcon(qta.icon(self.icon_id))
        self.setEnabled(False)
        self.setStyleSheet("padding: 8px;")
        self.setProperty("class", "navbtns")

        controller.currentBrowserChanged.connect(self.set_browser)
    
    def set_browser(self, browser):
        if self.browser:
            self.browser.iconChanged.disconnect(self.update_status)
            self.browser.urlChanged.disconnect(self.update_status)

        self.browser = browser

        self.browser.iconChanged.connect(self.update_status)
        self.browser.urlChanged.connect(self.update_status)
        self.clicked.connect(self.go_back)

        self.update_status()
    
    def update_status(self):
        self.setEnabled(self.browser.history().canGoBack())

    def update_icon_color(self, icon_color: str):
        self.icon_color = icon_color
        self.setIcon(qta.icon(self.icon_id, color=icon_color))
    
    def go_back(self):
        if self.browser:
            self.browser.back()

class ForwardBtn(QPushButton):
    def __init__(self, controller, parent = None):
        super().__init__(parent)

        self.browser: BetterWebEngine = None
        self.icon_id = "fa6s.arrow-right"
        self.icon_color = "white"

        self.setIcon(qta.icon(self.icon_id))
        self.setEnabled(False)
        self.setStyleSheet("padding: 8px;")
        self.setProperty("class", "navbtns")

        controller.currentBrowserChanged.connect(self.set_browser)
    
    def set_browser(self, browser):
        if self.browser:
            self.browser.iconChanged.disconnect(self.update_status)
            self.browser.urlChanged.disconnect(self.update_status)

        self.browser = browser

        self.browser.iconChanged.connect(self.update_status)
        self.browser.urlChanged.connect(self.update_status)
        self.clicked.connect(self.go_forward)

        self.update_status()
    
    def update_status(self):
        self.setEnabled(self.browser.history().canGoForward())
    
    def update_icon_color(self, icon_color: str):
        self.icon_color = icon_color
        self.setIcon(qta.icon(self.icon_id, color=icon_color))
    
    def go_forward(self):
        if self.browser:
            self.browser.forward()
        
class ReloadBtn(QPushButton):
    def __init__(self, controller, parent = None):
        super().__init__(parent)

        self.browser: BetterWebEngine = None
        self.icon_id = "fa6s.arrow-rotate-right"
        self.icon_color = "white"

        self.setIcon(qta.icon(self.icon_id))
        self.setStyleSheet("padding: 8px;")
        self.setProperty("class", "navbtns")

        controller.currentBrowserChanged.connect(self.set_browser)
    
    def set_browser(self, browser):
        if self.browser:
            self.browser.loadStarted.disconnect(self.update_status)
            self.browser.loadFinished.disconnect(self.update_status)
            self.browser.loadProgress.disconnect(self.update_status)

        self.browser = browser

        self.browser.loadStarted.connect(self.update_status)
        self.browser.loadFinished.connect(self.update_status)
        self.browser.loadProgress.connect(self.update_status)
        self.clicked.connect(self.trigger_reload_stop)

        self.update_status()
    
    def update_status(self):
        if self.browser.page_is_loading:
            self.icon_id = "ei.remove"

        else:
            self.icon_id = "fa6s.arrow-rotate-right"
        
        self.setIcon(qta.icon(self.icon_id, color=self.icon_color))
    
    def update_icon_color(self, icon_color: str):
        self.icon_color = icon_color
        self.setIcon(qta.icon(self.icon_id, color=icon_color))
    
    def trigger_reload_stop(self):
        if self.browser:
            if self.browser.page_is_loading:
                self.browser.stop_page()
            
            else:
                self.browser.reload_page()
        
            self.update_status()

class ExtSidebarBtn(QPushButton):
    def __init__(self, ui_controller):
        super().__init__()
        
        self.ui_controller = ui_controller

        self.icon_id = "msc.layout-sidebar-left"
        self.icon_color = "white"
        
        self.setIcon(qta.icon(self.icon_id))
        self.setStyleSheet("padding: 8px;")
        self.setProperty("class", "navbtns")

        self.clicked.connect(self.toggle_sidebar)
    
    def toggle_sidebar(self):
        self.ui_controller.toggle_sidebar()
    
    def update_icon_color(self, icon_color: str):
        self.icon_color = icon_color
        self.setIcon(qta.icon(self.icon_id, color=icon_color))

class TabManagerBtn(QPushButton):
    def __init__(self, ui_controller):
        super().__init__()
        
        self.ui_controller = ui_controller

        self.icon_id = "ri.menu-fill"
        self.icon_color = "white"
        
        self.setIcon(qta.icon(self.icon_id))
        self.setStyleSheet("padding: 8px;")
        self.setProperty("class", "navbtns")

        self.clicked.connect(self.toggle_sidebar)
    
    def toggle_sidebar(self):
        self.ui_controller.toggle_tab_manager()
    
    def update_icon_color(self, icon_color: str):
        self.icon_color = icon_color
        self.setIcon(qta.icon(self.icon_id, color=icon_color))

class GoBtn(QPushButton):
    def __init__(self, controller, parent = None):
        super().__init__(parent)

        self.browser: BetterWebEngine = None
        self.icon_id = "mdi.arrow-right-bold-box"
        self.icon_color = "white"
        self.controller = controller

        self.setIcon(qta.icon(self.icon_id))
        self.setStyleSheet("padding: 8px;")
        self.setProperty("class", "navbtns")

        self.controller.currentBrowserChanged.connect(self.set_browser)
    
    def set_browser(self, browser):
        if self.browser:
            self.browser.urlChanged.disconnect(self.update_status)

        self.browser = browser

        self.browser.urlChanged.connect(self.update_status)
        self.clicked.connect(self.go_to_url)

        self.update_status()
    
    def update_status(self):
        pass
    
    def update_icon_color(self, icon_color: str):
        self.icon_color = icon_color
        self.setIcon(qta.icon(self.icon_id, color=icon_color))
    
    def go_to_url(self):
        if self.browser:
            adress_bar = self.controller.get_first_widget_from_navbar(AddressBar)
            if adress_bar:
                url = adress_bar.text()
                self.browser.load_page(url)

class DownloadManagerBtn(QPushButton):
    def __init__(self, controller, parent = None):
        super().__init__(parent)

        self.controller = controller
        self.icon_id = "fa6s.download"
        self.icon_color = "white"

        self.setIcon(qta.icon(self.icon_id))
        self.setStyleSheet("padding: 8px;")
        self.setProperty("class", "navbtns")

        self.setVisible(False)
        self.clicked.connect(self.open_download_menu)
    
    def open_download_menu(self):
        self.controller.open_download_menu(self)
    
    def update_icon_color(self, icon_color: str):
        self.icon_color = icon_color
        self.setIcon(qta.icon(self.icon_id, color=icon_color))

class ZoomInBtn(QPushButton):
    def __init__(self, controller, parent = None):
        super().__init__(parent)

        self.browser: BetterWebEngine = None
        self.icon_id = "ph.magnifying-glass-plus"
        self.icon_color = "white"

        self.setIcon(qta.icon(self.icon_id))
        self.setStyleSheet("padding: 8px;")
        self.setProperty("class", "navbtns")

        controller.currentBrowserChanged.connect(self.set_browser)
    
    def set_browser(self, browser):
        self.browser = browser
        self.clicked.connect(self.zoom_in)
    
    def update_icon_color(self, icon_color: str):
        self.icon_color = icon_color
        self.setIcon(qta.icon(self.icon_id, color=icon_color))
    
    def zoom_in(self):
        if self.browser:
            self.browser.scale_page_up()

class ZoomOutBtn(QPushButton):
    def __init__(self, controller, parent = None):
        super().__init__(parent)

        self.browser: BetterWebEngine = None
        self.icon_id = "ph.magnifying-glass-minus"
        self.icon_color = "white"

        self.setIcon(qta.icon(self.icon_id))
        self.setStyleSheet("padding: 8px;")
        self.setProperty("class", "navbtns")

        controller.currentBrowserChanged.connect(self.set_browser)
    
    def set_browser(self, browser):
        self.browser = browser
        self.clicked.connect(self.zoom_in)
    
    def update_icon_color(self, icon_color: str):
        self.icon_color = icon_color
        self.setIcon(qta.icon(self.icon_id, color=icon_color))
    
    def zoom_in(self):
        if self.browser:
            self.browser.scale_page_down()

class ZoomAmountLabel(QLabel):
    def __init__(self, controller, parent = None):
        super().__init__(parent)

        self.browser: BetterWebEngine = None
        self.setStyleSheet("padding: 8px;")

        controller.currentBrowserChanged.connect(self.set_browser)
    
    def set_browser(self, browser):
        if self.browser:
            self.browser.signals.zoom_factor_changed.disconnect(self.update_factor)
        
        self.browser = browser
        self.browser.signals.zoom_factor_changed.connect(self.update_factor)

        self.update_factor(self.browser.zoomFactor())
    
    def update_factor(self, factor):
        if self.browser:
            zoom_string = str(round(factor * 100)) + "%"
            self.setText(zoom_string)

class PageProgressBar(QProgressBar):
    def __init__(self, controller, parent = None):
        super().__init__(parent)

        self.browser: BetterWebEngine = None
        self.setFixedWidth(250)
        self.setTextVisible(True)

        controller.currentBrowserChanged.connect(self.set_browser)
    
    def set_browser(self, browser):
        if self.browser:
            self.browser.loadProgress.disconnect(self.update_progress)
            self.browser.loadStarted.disconnect(self.show_pb)
            self.browser.loadFinished.disconnect(self.hide_pb)
        
        self.browser = browser
        self.browser.loadProgress.connect(self.update_progress)
        self.browser.loadStarted.connect(self.show_pb)
        self.browser.loadFinished.connect(self.hide_pb)
    
    def update_progress(self, progress):
        if self.browser:
            self.setValue(progress)
        
    def show_pb(self):
        if self.browser:
            self.setVisible(True)
    
    def hide_pb(self):
        if self.browser:
            self.setVisible(False)