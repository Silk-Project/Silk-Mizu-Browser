from PySide6.QtGui import QColor
import qdarktheme
import darkdetect

class ThemeManager():
    def __init__(self, applic, additional_qss, accent_color="#8370EB", theme="dark"):
        self.applic = applic
        self.theme = theme
        self.additional_qss = additional_qss
        self.custom_colors = {
            "primary": QColor(accent_color).name()
        }
        self.available_themes = [
            "light",
            "dark",
            "auto",
            "legacy"
        ]
        self.load_theme(theme)

    def load_theme(self, theme_input):
        theme_input = theme_input.strip().lower()

        if theme_input in self.available_themes:
            if theme_input != "auto" and theme_input != "legacy":
                qdarktheme.setup_theme(theme_input, custom_colors=self.custom_colors, additional_qss=self.additional_qss)

            elif theme_input == "auto":
                qdarktheme.setup_theme("auto", custom_colors=self.custom_colors, additional_qss=self.additional_qss)

            elif theme_input == "legacy":
                self.applic.setStyleSheet(self.additional_qss)

            self.theme = theme_input

        else:
            print("Theme not found")

    def load_theme_from_index(self, index):
        theme = self.available_themes[index]
        self.load_theme(theme)

    def set_accent_color(self, color: QColor):
        if self.theme == "legacy":
            return

        self.custom_colors["primary"] = color
        qdarktheme.setup_theme(self.theme, custom_colors=self.custom_colors, additional_qss=self.additional_qss)

    def get_plain_theme(self):
        if self.theme != "auto" and self.theme != "legacy":
            return self.theme

        else:
            system_theme = "dark" if darkdetect.isDark() else "light"
            return system_theme

    def get_contrast_color_from_theme(self):
        if self.get_plain_theme() == "light":
            return "black"
        else:
            return "white"