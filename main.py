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
import random
import sys
from pathlib import Path
from platformdirs import user_config_dir
import qdarkstyle
from PyQt6.QtWidgets import QMainWindow, QApplication, QStackedWidget, QFileDialog, QVBoxLayout, QSystemTrayIcon, QMenu
from PyQt6.QtCore import QEvent, Qt, QFileSelector, QTimer
from PyQt6.QtGui import QMouseEvent, QIcon, QAction, QCloseEvent
from PyQt6 import uic
from data.classes import PictureViewer, StatisticWidget, resource_path, SettingsWidget, ConfigObject
from loguru import logger
from data.constants import *

# pyinstaller --icon=image.ico --onefile --noconsole --add-data "data;data" --name=PicureViewer  main.py


user_data = {
    "last_folder": "",
    "pictures_copied": 0,
    "pictures_loaded": 0,
    #Maybe later :\
    "most_popular_picture": ''
}
user_statistic = ConfigObject('config.yml')


settings = {
    'Theme': DARK,
    "Sorting": SORT_BY_NAME_A_TO_Z
}

settings_object = ConfigObject('settings.yml')


class Window(QMainWindow):
    #Last copied image
    last_image: None | PictureViewer = None

    def __init__(self):
        super().__init__()
        self.all_files = None
        self.pictures = []
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.scenes = {}
        self._preload_scenes()

        self.switch_to_scene('main')

        self.init_tray_icon()

        self.setWindowTitle('Pictures Viewer')
        self.setWindowIcon(QIcon(resource_path('data/images/image.png')))

    def get_scene(self, name):
        return self.scenes.get(name)

    def _preload_scenes(self):
        self.setFixedSize(1200, 800)

        main_widget = uic.loadUi(resource_path('data/scenes/main.ui'))
        self.stacked_widget.addWidget(main_widget)
        self.scenes['main'] = main_widget

        scroll_contents = main_widget.picturesArea.widget()
        if scroll_contents.layout() is None:
            self.pictures_layout = QVBoxLayout(scroll_contents)
            self.pictures_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            scroll_contents.setLayout(self.pictures_layout)

        main_widget.folderLoadProgressBar.setValue(0)

        self._connect_signal()

    def _connect_signal(self):
        main = self.get_scene('main')
        main.actionChoose_a_folder_2.triggered.connect(self.choose_folder)
        main.Search.textChanged.connect(self.search)
        main.copyRandom.clicked.connect(self.copy_random)
        main.actionshowStatistics.triggered.connect(self.open_statistic)
        main.actionSettings.triggered.connect(self.open_settings)

        main.sortBy.currentIndexChanged.connect(lambda a: self.set_sorting(a+2))
        main.sortBy.activated.connect(lambda a: self.set_sorting(a+2))

    def switch_to_scene(self, name):
        if name in self.scenes:
            self.stacked_widget.setCurrentWidget(self.scenes.get(name))

    def choose_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self)
        if folder_path:
            print(folder_path)
            user_data['last_folder'] = folder_path
            self.open_pictures(folder_path)

    def delete_pictures(self):
        if self.pictures:
            for picture in self.pictures:
                self.pictures_layout.removeWidget(picture)

    def open_pictures(self, path):
        main_scene = self.get_scene('main')

        self.delete_pictures()
        self.pictures.clear()

        self.all_files = []
        for file in os.listdir(path):
            if file.split('.')[-1] in ['png', 'jpg', 'jpeg', 'svg', 'webp', 'bmp']:
                full_file_path = f'{path}/{file}'

                self.all_files.append(full_file_path)
                user_data['pictures_loaded'] += 1
        main_scene.folderLoadProgressBar.setMaximum(len(self.all_files))

        self.spawn_pictures_objects(self.all_files)

        for setting in settings:
            self.set_setting(setting, settings[setting])

    def spawn_pictures_objects(self, all_files):
        main_scene = self.get_scene('main')
        main_scene.folderLoadProgressBar.setValue(0)
        for i, full_file_path in enumerate(all_files):
            logger.info('Try to create PictureViewer')
            picture = PictureViewer(self)

            logger.info('Try to set image file')
            picture.set_file(full_file_path)
            self.pictures.append(picture)

            logger.info('Try to add this on a window')
            self.pictures_layout.addWidget(picture)

            logger.success(f'{full_file_path} added on the screen')
            main_scene.folderLoadProgressBar.setValue(i + 1)

    def spawn_pictures_object_by_pictures_list(self):
        main_scene = self.get_scene('main')
        main_scene.folderLoadProgressBar.setValue(0)

        for i, picture in enumerate(self.pictures):
            self.pictures_layout.addWidget(picture)
            main_scene.folderLoadProgressBar.setValue(i + 1)

    def on_picture_copy(self):
        user_data['pictures_copied'] += 1

    def open_statistic(self):
        self.statistic_window = StatisticWidget(self, user_data, settings)
        self.statistic_window.show()

    def open_settings(self):
        self.settings_window = SettingsWidget(self, settings)
        self.settings_window.show()

    def copy_random(self):
        if not self.pictures:
            return

        random_picture = random.choice(self.pictures)
        random_picture.copy()

    def search(self, word):
        if not self.pictures:
            return

        for p in self.pictures:
            if word in p.file_name:
                p.show()
            else:
                p.hide()

    def set_setting(self, par: str, val: str):
        match par:
            case 'Theme':
                self.setStyleSheet(qdarkstyle.load_stylesheet(qdarkstyle.LightPalette if int(val) == LIGHT else qdarkstyle.DarkPalette))
                settings['Theme'] = int(val)
            case 'Sorting':
                self.get_scene('main').sortBy.setCurrentIndex(int(val)-2)
                self.set_sorting(int(val))

    def set_sorting(self, method: int):
        settings['Sorting'] = method
        match method:
            case 2:
                self.pictures.sort(key=lambda x: x.file_name)
            case 3:
                self.pictures.sort(key=lambda x: x.file_name, reverse=True)
            case 4:
                random.shuffle(self.pictures)
        self.spawn_pictures_object_by_pictures_list()


    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(resource_path('data/images/image.png')))
        self.tray_icon.setToolTip('Image Viewer')

        tray_menu = QMenu()

        show_action = QAction('Show', self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)

        copy_last_action = QAction('Copy last picture', self)
        copy_last_action.triggered.connect(lambda: self.last_image.copy() if self.last_image else None)
        tray_menu.addAction(copy_last_action)

        copy_random_action = QAction('Copy random picture', self)
        copy_random_action.triggered.connect(self.copy_random)
        tray_menu.addAction(copy_random_action)

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close_in_tray)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def close_in_tray(self):
        user_statistic.save_user_data(user_data)
        settings_object.save_user_data(settings)
        sys.exit(0)

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent):
        event.ignore()
        self.hide()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_point = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_point is not None:
            delta = event.globalPosition().toPoint() - self._drag_point
            self.move(self.pos() + delta)
            self._drag_point = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_point = None


if __name__ == "__main__":
    user_data = user_statistic.load_user_data(user_data)
    settings = settings_object.load_user_data(settings)

    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    window = Window()

    window.show()

    if len(user_data['last_folder']):
        QTimer.singleShot(200, lambda: window.open_pictures(user_data['last_folder']))

    sys.exit(app.exec())
