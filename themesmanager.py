from functools import partial
from itertools import chain
import os
import re
from PyQt5.QtWidgets import QAction, QActionGroup
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QPixmap
from constants import Constants
from switchable_label import SwitchableLabelsIterable
from utilities import pop_up


class ThemeConstants:
    """Container class for all the relevant theme-related constants."""

    FOLDER                    = "themes"
    EXTENSION                 = ".qss"
    ICONS_FOLDER              = "icons"
    DEFAULT                   = "dark"
    CURRENT                   = ".current_theme"
    COLORS                    = "colors.txt"
    COLOR_SEPARATOR           = "="
    DEFAULT_ACTIVE_COLOR      = "#000000"
    DEFAULT_INACTIVE_COLOR    = "#9f9f9f"
    DEFAULT_OFF_COLORS        = "#000000", "#434343"
    DEFAULT_ON_COLORS         = "#4b79a1", "#283e51"
    DEFAULT_TEXT_COLOR        = "#ffffff"
    THEME_NOT_FOUND           = "Theme not found"
    MISSING_THEME             = "Missing theme in '" + FOLDER + "' folder."
    MISSING_THEME_FOLDER      = "'" + FOLDER + "'" + " folder not found.\nOnly the basic theme is available."
    THEME_FOLDER_NOT_FOUND    = "'" + FOLDER + "'" + " folder not found"
    DEFAULT_ICONS_PATH        = os.path.join(FOLDER, DEFAULT, ICONS_FOLDER)
    DEFAULT_SEARCH_LABEL_PATH = os.path.join(DEFAULT_ICONS_PATH, Constants.SEARCH_LABEL_IMG)
    DEFAULT_VOLUME_LABEL_PATH = os.path.join(DEFAULT_ICONS_PATH, Constants.VOLUME_LABEL_IMG)
    CURRENT_THEME_FILE        = os.path.join(FOLDER, CURRENT)
    DEFAULT_THEME_PATH        = os.path.join(FOLDER, DEFAULT)


class ThemeManager:
    """Manage all the operations releted the the themes."""

    def __init__(self, parent):
        """Initialize the ThemeManager instance."""
        self.__parent = parent
        self.__parent.active_color = ThemeConstants.DEFAULT_ACTIVE_COLOR
        self.__parent.inactive_color = ThemeConstants.DEFAULT_INACTIVE_COLOR

        self.__theme_path = ""
        self.__current_theme = ""

        self.__space_weather_labels = SwitchableLabelsIterable(
            *list(
                chain(
                    self.__parent.switchable_r_labels,
                    self.__parent.switchable_s_labels,
                    self.__parent.switchable_g_now_labels,
                    self.__parent.switchable_g_today_labels,
                    self.__parent.k_storm_labels,
                    self.__parent.a_storm_labels,
                    [self.__parent.expected_noise_lbl]
                )
            )
        )

        self.__space_weather_labels.set(
            "switch_on_colors",
            ThemeConstants.DEFAULT_ON_COLORS
        )
        self.__space_weather_labels.set(
            "switch_off_colors", ThemeConstants.DEFAULT_OFF_COLORS
        )

        self.__theme_names = {}

    def __refresh_range_labels(self):
        """Refresh the range-labels."""
        self.__parent.set_acf_interval_label()
        self.__parent.set_band_filter_label(
            self.__parent.activate_low_band_filter_btn,
            self.__parent.lower_band_spinbox,
            self.__parent.lower_band_filter_unit,
            self.__parent.lower_band_confidence,
            self.__parent.activate_up_band_filter_btn,
            self.__parent.upper_band_spinbox,
            self.__parent.upper_band_filter_unit,
            self.__parent.upper_band_confidence,
            self.__parent.band_range_lbl
        )

        self.__parent.set_band_filter_label(
            self.__parent.activate_low_freq_filter_btn,
            self.__parent.lower_freq_spinbox,
            self.__parent.lower_freq_filter_unit,
            self.__parent.lower_freq_confidence,
            self.__parent.activate_up_freq_filter_btn,
            self.__parent.upper_freq_spinbox,
            self.__parent.upper_freq_filter_unit,
            self.__parent.upper_freq_confidence,
            self.__parent.freq_range_lbl
        )

    @pyqtSlot()
    def __apply(self, theme_path):
        """Apply the selected theme.

        Refresh all relevant widgets.
        Display a QMessageBox if the theme is not found."""
        self.__theme_path = theme_path
        if os.path.exists(theme_path):
            if self.__theme_path != self.__current_theme:
                self.__change()
                self.__parent.display_specs(
                    item=self.__parent.signals_list.currentItem(),
                    previous_item=None
                )
                self.__refresh_range_labels()
                self.__parent.audio_widget.refresh_btns_colors(
                    self.__parent.active_color,
                    self.__parent.inactive_color
                )
                self.__space_weather_labels.refresh()
        else:
            pop_up(self.__parent, title=ThemeConstants.THEME_NOT_FOUND,
                   text=ThemeConstants.MISSING_THEME).show()

    def __pretty_name(self, bad_name):
        """Return a well-formatted theme name."""
        return ' '.join(
            map(lambda s: s.capitalize(),
                bad_name.split('_')
            )
        )

    def __detect_themes(self):
        """Detect all available themes.

        Connect all the actions to change the theme.
        Display a QMessageBox if the theme folder is not found."""
        themes = []
        ag = QActionGroup(self.__parent, exclusive=True)
        if os.path.exists(ThemeConstants.FOLDER):
            for theme_folder in sorted(os.listdir(ThemeConstants.FOLDER)):
                relative_folder = os.path.join(ThemeConstants.FOLDER, theme_folder)
                if os.path.isdir(os.path.abspath(relative_folder)):
                    relative_folder = os.path.join(ThemeConstants.FOLDER, theme_folder)
                    themes.append(relative_folder)
            for theme_path in themes:
                theme_name = '&' + self.__pretty_name(os.path.basename(theme_path))
                new_theme = ag.addAction(
                    QAction(
                        theme_name,
                        self.__parent, checkable=True
                    )
                )
                self.__parent.menu_themes.addAction(new_theme)
                self.__theme_names[theme_name.lstrip('&')] = new_theme
                new_theme.triggered.connect(partial(self.__apply, theme_path))
        else:
            pop_up(self.__parent, title=ThemeConstants.THEME_FOLDER_NOT_FOUND,
                   text=ThemeConstants.MISSING_THEME_FOLDER).show()

    def __is_valid_html_color(self, colors):
        """Return if a string or a list of strings has a valid html format."""
        pattern = "#([a-zA-Z0-9]){6}"
        match_ok = lambda col: bool(re.match(pattern, col))
        if isinstance(colors, list):
            if len(colors) > 1:
                return all(match_ok(c) for c in colors)
            else:
                return match_ok(colors[0])
        else:
            return match_ok(colors)

    def __change(self):
        """Change the current theme.

         Apply the stylesheet and set active and inactive colors.
         Set all the new images needed.
         Save the new current theme on file."""
        theme_name = os.path.basename(self.__theme_path) + ThemeConstants.EXTENSION
        try:
            with open(
                os.path.join(self.__theme_path, theme_name), "r"
            ) as stylesheet:
                style = stylesheet.read()
                self.__parent.setStyleSheet(style)
                self.__parent.download_window.setStyleSheet(style)
        except FileNotFoundError:
            pop_up(self.__parent, title=ThemeConstants.THEME_NOT_FOUND,
                   text=ThemeConstants.MISSING_THEME).show()
        else:
            icons_path = os.path.join(self.__theme_path, ThemeConstants.ICONS_FOLDER)

            path_to_search_label = os.path.join(
                icons_path,
                Constants.SEARCH_LABEL_IMG
            )

            if os.path.exists(path_to_search_label):
                path = path_to_search_label
            else:
                path = ThemeConstants.DEFAULT_SEARCH_LABEL_PATH

            self.__parent.search_label.setPixmap(
                QPixmap(path)
            )
            self.__parent.modulation_search_label.setPixmap(
                QPixmap(path)
            )
            self.__parent.location_search_label.setPixmap(
                QPixmap(path)
            )

            self.__parent.search_label.setScaledContents(True)
            self.__parent.modulation_search_label.setScaledContents(True)
            self.__parent.location_search_label.setScaledContents(True)

            path_to_volume_label = os.path.join(
                icons_path,
                Constants.VOLUME_LABEL_IMG
            )

            if os.path.exists(path_to_volume_label):
                path = path_to_volume_label
            else:
                path = ThemeConstants.DEFAULT_VOLUME_LABEL_PATH

            self.__parent.volume_label.setPixmap(
                QPixmap(path)
            )

            self.__parent.volume_label.setScaledContents(True)

            path_to_colors = os.path.join(
                self.__theme_path,
                ThemeConstants.COLORS
            )

            active_color_ok     = False
            inactive_color_ok   = False
            switch_on_color_ok  = False
            switch_off_color_ok = False
            text_color_ok       = False

            if os.path.exists(path_to_colors):
                with open(path_to_colors, "r") as colors_file:
                    for line in colors_file:
                        if ThemeConstants.COLOR_SEPARATOR in line:
                            quality, color = line.split(ThemeConstants.COLOR_SEPARATOR)
                            color = color.rstrip()
                            color_len = 1
                            if ',' in color:
                                color = [c.strip() for c in color.split(',')]
                                color_len = len(color)
                            if self.__is_valid_html_color(color):
                                if color_len == 1:
                                    if quality.lower() == Constants.ACTIVE:
                                        self.__parent.active_color = color
                                        active_color_ok = True
                                    if quality.lower() == Constants.INACTIVE:
                                        self.__parent.inactive_color = color
                                        inactive_color_ok = True
                                    if quality.lower() == Constants.TEXT_COLOR:
                                        text_color_ok = True
                                        self.__space_weather_labels.set(
                                            "text_color",
                                            color
                                        )
                                if color_len == 2:
                                    if quality.lower() == Constants.LABEL_ON_COLOR:
                                        switch_on_color_ok = True
                                        self.__space_weather_labels.set(
                                            "switch_on_colors",
                                            color
                                        )
                                    if quality.lower() == Constants.LABEL_OFF_COLOR:
                                        switch_off_color_ok = True
                                        self.__space_weather_labels.set(
                                            "switch_off_colors",
                                            color
                                        )

            if not (active_color_ok and inactive_color_ok):
                self.__parent.active_color = ThemeConstants.DEFAULT_ACTIVE_COLOR
                self.__parent.inactive_color = ThemeConstants.DEFAULT_INACTIVE_COLOR

            if not (switch_on_color_ok and switch_off_color_ok):
                self.__space_weather_labels.set(
                    "switch_on_colors",
                    ThemeConstants.DEFAULT_ON_COLORS
                )
                self.__space_weather_labels.set(
                    "switch_off_colors",
                    ThemeConstants.DEFAULT_OFF_COLORS
                )

            if not text_color_ok:
                self.__space_weather_labels.set(
                    "text_color",
                    ThemeConstants.DEFAULT_TEXT_COLOR
                )
            self.__current_theme = self.__theme_path

            try:
                with open(ThemeConstants.CURRENT_THEME_FILE, "w") as current_theme:
                    current_theme.write(self.__theme_path)
            except Exception:
                pass

    def start(self):
        """Start the theme manager."""
        self.__detect_themes()
        if os.path.exists(ThemeConstants.CURRENT_THEME_FILE):
            with open(ThemeConstants.CURRENT_THEME_FILE, "r") as current_theme_path:
                theme_path = current_theme_path.read()
                theme_name = self.__pretty_name(os.path.basename(theme_path))
                try:
                    self.__theme_names[theme_name].setChecked(True)
                except Exception:
                    pop_up(self.__parent, title=ThemeConstants.THEME_NOT_FOUND,
                           text=ThemeConstants.MISSING_THEME).show()
                else:
                    self.__apply(theme_path)
        else:
            try:
                self.__theme_names[
                    self.__pretty_name(ThemeConstants.DEFAULT)
                ].setChecked(True)
            except Exception:
                pop_up(self.__parent, title=ThemeConstants.THEME_NOT_FOUND,
                       text=ThemeConstants.MISSING_THEME).show()
            else:
                self.__apply(ThemeConstants.DEFAULT_THEME_PATH)
