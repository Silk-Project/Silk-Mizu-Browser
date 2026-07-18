import qtawesome as qta
from PySide6.QtWidgets import (
    QPushButton,
    QLineEdit,
    QLabel,
    QWidget,
    QSizePolicy,
    QHBoxLayout,
)
from interface.navigation.nav_items import (
    AddressBar, 
    BackBtn, 
    ForwardBtn, 
    ReloadBtn, 
    ExtSidebarBtn,
    TabManagerBtn,
    HistoryManagerBtn,
    GoBtn,
    DownloadManagerBtn,
    ZoomInBtn,
    ZoomOutBtn,
    ZoomAmountLabel,
    PageProgressBar,
    ClockLabel,
)
from interface.dialogs.manage_navbar_dialog import NavigationUIElement, NavigationUIAdditionalStyling

class NavBarManager(QWidget):
    def __init__(self, controller, theme_mgr=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.theme_mgr = theme_mgr

        self.controls_layout = QHBoxLayout()
        self.controls_layout.setContentsMargins(5, 5, 5, 5)
        self.controls_layout.setSpacing(5)
        self.setLayout(self.controls_layout)

    def rebuild_navbar(self, elements: list):
        try:
            while self.controls_layout.count():
                item = self.controls_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            if not elements:
                return 1

            for raw in elements:
                try:
                    if isinstance(raw, NavigationUIElement):
                        element = raw
                    elif isinstance(raw, dict):
                        element = self._dict_to_element(raw)
                    else:
                        continue

                    widget = self._create_navbtn(element)
                    if widget is not None:
                        self.controls_layout.addWidget(widget)
                except Exception as e:
                    print(f"Error creating navbar element: {e}")
                    continue
        except Exception as e:
            print(f"Error rebuilding navbar: {e}")

    def _dict_to_element(self, d: dict) -> NavigationUIElement:
        styling_data = d.get("styling")

        if styling_data and isinstance(styling_data, dict):
            try:
                styling = NavigationUIAdditionalStyling(**styling_data)
            except Exception:
                styling = NavigationUIAdditionalStyling()
        else:
            styling = NavigationUIAdditionalStyling()

        return NavigationUIElement(
            name=d.get("name", ""),
            type=d.get("type", ""),
            icon=d.get("icon"),
            action=d.get("action", ""),
            styling=styling,
        )

    def _create_navbtn(self, element: NavigationUIElement):
        try:
            if element.type == "button":
                if element.styling and element.styling.icon_color:
                    icon_color = element.styling.icon_color
                else:
                    try:
                        icon_color = self.theme_mgr.get_contrast_color_from_theme()
                    except Exception:
                        icon_color = "white"

                if element.action == "back":
                    button = BackBtn(controller=self.controller, icon=element.icon)
                    button.update_icon_color(icon_color)

                elif element.action == "forward":
                    button = ForwardBtn(controller=self.controller, icon=element.icon)
                    button.update_icon_color(icon_color)

                elif element.action == "reload":
                    button = ReloadBtn(controller=self.controller, icon=element.icon)
                    button.update_icon_color(icon_color)

                elif element.action == "go":
                    button = GoBtn(controller=self.controller, icon=element.icon)
                    button.update_icon_color(icon_color)

                elif element.action == "new_tab":
                    button = QPushButton()
                    button.setStyleSheet("padding: 8px;")
                    button.setProperty("class", "navbtns")
                    button.setIcon(qta.icon(element.icon, color=icon_color))
                    button.clicked.connect(self.controller.window.create_new_tab)

                elif element.action in ("download_manager", "downloads"):
                    button = DownloadManagerBtn(controller=self.controller, icon=element.icon)
                    button.update_icon_color(icon_color)

                elif element.action == "add_bookmark":
                    button = QPushButton()
                    button.setStyleSheet("padding: 8px;")
                    button.setProperty("class", "navbtns")
                    button.setIcon(qta.icon("fa5s.bookmark", color=icon_color))
                    button.clicked.connect(self.controller.window.add_current_to_bookmarks_dialog)

                elif element.action == "extensions":
                    button = QPushButton()
                    button.setStyleSheet("padding: 8px;")
                    button.setProperty("class", "navbtns")
                    button.setIcon(qta.icon("mdi6.puzzle", color=icon_color))
                    button.clicked.connect(self.controller.window.web_extension_dialog)

                elif element.action == "settings":
                    button = QPushButton()
                    button.setStyleSheet("padding: 8px;")
                    button.setProperty("class", "navbtns")
                    button.setIcon(qta.icon("fa5s.cog", color=icon_color))
                    button.clicked.connect(self.controller.window.settings_dialog)

                elif element.action == "extensions_sidebar":
                    button = ExtSidebarBtn(controller=self.controller, icon=element.icon)
                    button.update_icon_color(icon_color)
                
                elif element.action == "tab_manager":
                    button = TabManagerBtn(ui_controller=self.controller, icon=element.icon)
                    button.update_icon_color(icon_color)
                
                elif element.action == "history_manager":
                    button = HistoryManagerBtn(ui_controller=self.controller, icon=element.icon)
                    button.update_icon_color(icon_color)
                
                elif element.action == "zoom_in":
                    button = ZoomInBtn(controller=self.controller, icon=element.icon)
                    button.update_icon_color(icon_color)
                
                elif element.action == "zoom_out":
                    button = ZoomOutBtn(controller=self.controller, icon=element.icon)
                    button.update_icon_color(icon_color)

                else:
                    button = QPushButton()
                    button.setToolTip(element.action)
                    button.setStyleSheet("padding: 8px;")
                    button.setProperty("class", "navbtns")
                    if element.icon:
                        button.setIcon(qta.icon(element.icon, color=icon_color))
                    else:
                        button.setIcon(qta.icon("fa6s.question", color=icon_color))

                self._apply_styling_to_widget(button, element.styling)
                return button

            elif element.type == "urlbar" or element.type == "searchbar":
                line = AddressBar(self.controller)
                line.setStyleSheet("padding: 8px;")
                if element.type == "searchbar":
                    line.setPlaceholderText("Search...")
                else:
                    line.setPlaceholderText("https://")
                self._apply_styling_to_widget(line, element.styling)
                return line

            elif element.type == "spacer":
                spacer = QWidget()
                spacer.setStyleSheet("background: transparent; border: none;")
                spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                return spacer
            
            elif element.type == "label":
                label = QLabel()
                label.setStyleSheet("padding: 8px;")
                label.setText(element.styling.label if element.styling and element.styling.label else "")
                self._apply_styling_to_widget(label, element.styling)
                return label
            
            elif element.type == "dyn_label":
                if element.action == "zoom_label":
                    dyn_label = ZoomAmountLabel(self.controller)
                    self._apply_styling_to_widget(dyn_label, element.styling)
                    return dyn_label
                
                elif element.action == "clock":
                    dyn_label = ClockLabel(self.controller.timer)
                    self._apply_styling_to_widget(dyn_label, element.styling)
                    return dyn_label
            
            elif element.type == "progress_bar":
                if element.action == "page_progressbar":
                    progress_bar = PageProgressBar(self.controller)
                    return progress_bar

            else:
                label = QLabel(element.type)
                label.setStyleSheet("padding: 5px;")
                return label

        except Exception as e:
            print(f"Error creating navbar button for '{element.action}': {e}")
            return None

    def _apply_styling_to_widget(self, widget, styling: NavigationUIAdditionalStyling):
        try:
            if styling is None:
                return

            if styling.background_color:
                widget.setStyleSheet(
                    f"background-color: {styling.background_color}; padding: 8px;"
                )
            if styling.border_radius:
                existing = widget.styleSheet()
                widget.setStyleSheet(existing + f"border-radius: {styling.border_radius}px;")

            if isinstance(widget, QPushButton) and styling.label:
                widget.setText(styling.label)
            elif isinstance(widget, QLineEdit) and styling.label:
                widget.setPlaceholderText(styling.label)
            elif isinstance(widget, QLabel) and styling.label:
                widget.setText(styling.label)

            if isinstance(widget, QPushButton) and hasattr(widget, 'update_icon_color') and styling.icon_color:
                widget.update_icon_color(styling.icon_color)
            elif isinstance(widget, QPushButton) and styling.icon_color and hasattr(widget, 'icon_id'):
                widget.setIcon(qta.icon(widget.icon_id, color=styling.icon_color))
            elif isinstance(widget, QLabel) and styling.icon_color:
                existing = widget.styleSheet()
                widget.setStyleSheet(existing + f"color: {styling.icon_color};")
        except Exception as e:
            print(f"Error applying styling to widget: {e}")
