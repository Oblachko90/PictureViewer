# Picture Viewer
# Copyright (C) 2026 Oblachko90
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import sys

import qdarkstyle
from platformdirs import user_config_dir
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QApplication, QPushButton, QMainWindow
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt
from loguru import logger
from PyQt6 import uic
import yaml
from pathlib import Path
from data.constants import *


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class PictureViewer(QWidget):
    app = None

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.file_name = ''

        layout = QHBoxLayout()
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = QLabel()
        self.image_label.setMinimumSize(400, 400)

        self.file_name_label = QLabel()
        self.file_name_label.setStyleSheet("""
            QLabel{
                font-size: 25px;
                font-weight: bold;
            }
        """)

        self.copy_button = QPushButton()
        self.copy_button.setText("Copy to clipboard")
        self.copy_button.setFixedSize(400, 40)
        self.copy_button.clicked.connect(self.copy)

        layout.addWidget(self.image_label)
        layout.addLayout(right_layout)
        right_layout.addWidget(self.file_name_label)
        right_layout.addWidget(self.copy_button)

        self.setLayout(layout)

    def set_file(self, path):
        self.file_name = path.split('/')[-1]
        self.file_name_label.setText(path.split('/')[-1])
        pixmap = QPixmap(path)

        if pixmap.isNull():
            logger.warning(f'Cannot load this picture: {path}')
            return

        pixmap = pixmap.scaled(self.image_label.size()*0.8,
                               Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation
                               )

        self.image_label.setPixmap(pixmap)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def copy(self):
        pixmap = self.image_label.pixmap()

        clipboard = QApplication.clipboard()
        clipboard.setPixmap(pixmap)
        self.app.last_image = self
        self.app.on_picture_copy()


class DefaultWindow(QWidget):
    def __init__(self, settings_dict):
        super().__init__()
        self.setStyleSheet(qdarkstyle.load_stylesheet(qdarkstyle.DarkPalette if settings_dict['Theme'] == DARK else qdarkstyle.LightPalette))


class StatisticWidget(DefaultWindow):
    app = None

    def __init__(self, app, user_data, settings_dict):
        super().__init__(settings_dict)

        uic.loadUi(resource_path('data/scenes/statistic.ui'), self)
        self.setWindowTitle('PictureViewer: Statistic')

        format_data = ''
        for key in user_data:
            format_data += f"{key}: {user_data[key] if str(user_data[key]) else 'None'}\n"

        self.label_2.setText(format_data)


class SettingsWidget(DefaultWindow):
    app: None | QMainWindow = None
    current_settings: None | dict = None

    def __init__(self, app: QMainWindow, current_settings: dict):
        super().__init__(current_settings)

        uic.loadUi(resource_path('data/scenes/settings.ui'), self)
        self.setWindowTitle('PictureViewer: Settings')

        self.app = app
        self.current_settings = current_settings

        self.SetLightTheme.setChecked(current_settings['Theme'] == LIGHT)

        self.SetDarkTheme.toggled.connect(self.set_theme)
        self.SetLightTheme.toggled.connect(self.set_theme)

    def set_theme(self):
        current_theme = DARK if self.SetDarkTheme.isChecked() else LIGHT
        self.app.set_setting('Theme', str(current_theme))


class ConfigObject:
    filename: str
    config_path: Path
    config_dir: Path

    def __init__(self, filename):
        self.filename = filename

        self.config_dir = Path(user_config_dir('PictureViewer'))
        self.config_path = self.config_dir / self.filename

    def load_user_data(self, default_data):
        logger.info('Try to load user data')
        if not os.path.exists(self.config_path):
            logger.warning('Config file not found. Maybe first launch')
            return default_data
        logger.success('Config file found. Try to read')
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f'Failed to load config: {e}')

    def save_user_data(self, data):
        logger.info('Try to save user data')
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True)
            logger.success('User data save successful')
        except Exception as e:
            logger.error(f'Failed to save config: {e}')