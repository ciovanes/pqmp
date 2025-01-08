from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout,
							QHBoxLayout, QLabel, QFileDialog, QStyle, QSlider, QMenuBar, QMenu,
							QStatusBar, QToolBar, QCheckBox, QWidgetAction)
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtGui import QKeySequence, QIcon, QShortcut, QAction
import sys
import os
from recent_files_manager import RecentFilesManager
from functools import partial

class PQMP(QMainWindow):

    WINDOW_TITLE = "PQMP (PyQt Media Player)"

    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 720
    MINIMUM_WIDTH = 300
    MINIMUM_HEIGHT = 300

    DEFAULT_PLAYBACK_SPEED = 1.0
    DEFAULT_SKIP_TIME = 5000 #in ms

    MINIMUM_VOLUME = 0
    MAXIUM_VOLUME = 100
    DEFAULT_VOLUME_STEP = 5 # in %

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumSize(self.MINIMUM_WIDTH, self.MINIMUM_HEIGHT)
        self.resize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)

        # state variables
        self.is_fullscreen = False
        self.is_muted = False
        self.playback_speed = self.DEFAULT_PLAYBACK_SPEED

        self.recent_files_manager = RecentFilesManager()

        self.setup_ui()
        self.setup_shortcuts()
        self.setup_menubar()
        self.setup_statusbar()
        self.setup_signals()

        self.hide_controls_timer = QTimer()
        self.hide_controls_timer.setSingleShot(True)
        self.hide_controls_timer.timeout.connect(self.hide_controls)


    def setup_ui(self):
        # Centra widget and main layout
        self.centralWidget = QWidget(self)
        self.setCentralWidget(self.centralWidget)
        self.layout = QVBoxLayout(self.centralWidget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Configure media player
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        # Video widget
        self.video_widget = QVideoWidget()
        self.layout.addWidget(self.video_widget)
        self.media_player.setVideoOutput(self.video_widget)

        # Controls panel
        self.controls_widget = QWidget()
        self.controls_widget.setMaximumHeight(50)
        self.controls_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
            }
            QPushButton {
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: rgba(255, 255, 255, 0.2);
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: white;
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #0078D7;
                border: 1px solid #777;
                height: 8px;
                border-radius: 2px;
            }
            QSlider::add-page:horizontal {
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid #777;
                height: 8px;
                border-radius: 2px;
            }
        """)

        controls_layout = QVBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(10, 5, 10, 5)
        self.layout.addWidget(self.controls_widget)

        progress_layout = QHBoxLayout()
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.sliderMoved.connect(self.set_position)
        progress_layout.addWidget(self.progress_slider)

        # Time
        self.time_label = QLabel("0:00 / 0:00")
        progress_layout.addWidget(self.time_label)
        controls_layout.addLayout(progress_layout)

        # Playback controls
        playback_layout = QHBoxLayout()

        # Control buttons
        self.prev_button = QPushButton()
        self.prev_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        self.prev_button.setToolTip(f"Skip backward {self.DEFAULT_SKIP_TIME // 1000}s")

        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_button.setToolTip("Play\nIf the playlist is empyt, open a medium")

        self.next_button = QPushButton()
        self.next_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        self.next_button.setToolTip(f"Skip forward {self.DEFAULT_SKIP_TIME // 1000}s")

        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_button.setToolTip("Stop playback")

        # Volume control
        self.mute_button = QPushButton()
        self.mute_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        self.mute_button.setToolTip("Toggle mute")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(self.MINIMUM_VOLUME, self.MAXIUM_VOLUME)
        self.volume_slider.setValue(self.MAXIUM_VOLUME)
        self.volume_slider.setMaximumWidth(100)

        # Fullscreen button
        self.fullscreen_button = QPushButton()
        self.fullscreen_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))
        self.fullscreen_button.setToolTip("Toggle fullscreen")

        for widget in [self.prev_button, self.play_button, self.next_button,
                      self.stop_button, self.mute_button, self.volume_slider,
                      self.fullscreen_button]:
            playback_layout.addWidget(widget)

        playback_layout.addStretch()
        controls_layout.addLayout(playback_layout)

        # Connect buttons
        self.play_button.clicked.connect(self.play_pause)
        self.stop_button.clicked.connect(self.stop)
        self.mute_button.clicked.connect(self.toggle_mute)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)
        self.prev_button.clicked.connect(lambda: self.skip_backward(self.DEFAULT_SKIP_TIME))
        self.next_button.clicked.connect(lambda: self.skip_forward(self.DEFAULT_SKIP_TIME))

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Space"), self, self.play_pause)
        QShortcut(QKeySequence("Esc"), self, self.exit_fullscreen)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, lambda: self.skip_backward(self.DEFAULT_SKIP_TIME))
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, lambda: self.skip_forward(self.DEFAULT_SKIP_TIME))
        QShortcut(QKeySequence(Qt.Key.Key_Down), self, lambda: self.decrease_volume(self.DEFAULT_VOLUME_STEP))
        QShortcut(QKeySequence(Qt.Key.Key_Up), self, lambda: self.increase_volume(self.DEFAULT_VOLUME_STEP))

    def setup_menubar(self):
        self.menubar = self.menuBar()

        # Media
        media_menu = self.menubar.addMenu("Media")
        media_menu.setMinimumWidth(200)

        open_action = QAction(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)),
                            "Open file...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        media_menu.addAction(open_action)

        media_menu.addSeparator()

        self.recent_menu = media_menu.addMenu("Open Recent Files")
        self.update_recent_files_menu()

        media_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.quit_program)
        media_menu.addAction(quit_action)

        # Playback
        playback_menu = self.menubar.addMenu("Playback")
        playback_menu.setMinimumWidth(200)
        speed_menu = playback_menu.addMenu("Speed")
        speeds = [0.25, 0.5, 1.0, 1.5, 2.0]
        for speed in speeds:
            speed_action = QAction(f"{speed}x", self)
            speed_action.triggered.connect(lambda checked, s=speed: self.set_playback_speed(s))
            speed_menu.addAction(speed_action)

        playback_menu.addSeparator()

        play_action = QAction(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)),
                            "Play", self)
        play_action.triggered.connect(self.play_pause)
        playback_menu.addAction(play_action)

        stop_action = QAction(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)),
                            "Stop", self)
        stop_action.triggered.connect(self.stop)
        playback_menu.addAction(stop_action)

        skip_backward_action = QAction(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward)),
                            "Skip backward", self)
        skip_backward_action.triggered.connect(lambda: self.skip_backward(self.DEFAULT_SKIP_TIME))
        playback_menu.addAction(skip_backward_action)

        skip_forward_action = QAction(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward)),
                            "Skip forward", self)
        skip_forward_action.triggered.connect(lambda: self.skip_forward(self.DEFAULT_SKIP_TIME))
        playback_menu.addAction(skip_forward_action)

        # Audio
        audio_menu = self.menubar.addMenu("Audio")
        audio_menu.setMinimumWidth(200)

        increase_action = QAction(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume)),
                            "Increase Volume", self)
        increase_action.triggered.connect(lambda: self.increase_volume(self.DEFAULT_VOLUME_STEP))
        audio_menu.addAction(increase_action)

        decrease_action = QAction(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume)),
                            "Decrease Volume", self)
        decrease_action.triggered.connect(lambda: self.decrease_volume(self.DEFAULT_VOLUME_STEP))
        audio_menu.addAction(decrease_action)

        mute_action = QAction(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted)),
                            "Mute", self)
        mute_action.triggered.connect(self.toggle_mute)
        mute_action.setShortcut("M")
        audio_menu.addAction(mute_action)

        # Video
        video_menu = self.menubar.addMenu("Video")
        video_menu.setMinimumWidth(200)

        fullscreen_action = QAction(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon)),
                            "Fullscreen", self)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        fullscreen_action.setShortcut("F")
        video_menu.addAction(fullscreen_action)

        # View
        view_menu = self.menubar.addMenu("View")
        view_menu.setMinimumWidth(200)

        toggle_statusbar_action = QWidgetAction(self)
        self.checkbox_statusbar = QCheckBox("Show Statusbar")
        self.checkbox_statusbar.setChecked(True)
        toggle_statusbar_action.setDefaultWidget(self.checkbox_statusbar)
        view_menu.addAction(toggle_statusbar_action)

    def update_recent_files_menu(self):
        self.recent_menu.clear()
        recent_files = self.recent_files_manager.get_recent_files()

        for i, filepath in enumerate(recent_files, 1):
            action = QAction(os.path.basename(filepath), self)
            action.setData(filepath)
            action.triggered.connect(partial(self.open_recent_file, filepath))
            if i <= self.recent_files_manager.get_max_recent_files():
                action.setShortcut(f"Ctrl+{i}")
            self.recent_menu.addAction(action)

    def setup_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.current_status_message = "Ready"
        self.statusbar.showMessage(self.current_status_message)

    def toggle_statusbar(self, state):
        self.statusbar.setVisible(state == Qt.CheckState.Checked.value)
        if state == Qt.CheckState.Checked.value:
            self.statusbar.showMessage(self.current_status_message)

    def setup_signals(self):
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.errorOccurred.connect(self.handle_error)

        self.checkbox_statusbar.stateChanged.connect(self.toggle_statusbar)

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open video",
            "",
            "Video files (*.mp4 *.avi *.mkv *.mov);; All files (*.*)"
        )

        if filename:
            self.open_recent_file(filename)

    def open_recent_file(self, filename):
        if os.path.exists(filename):
            self.media_player.setSource(QUrl.fromLocalFile(filename))
            self.play_button.setEnabled(True)
            self.current_status_message = f"Playing: {os.path.basename(filename)}"
            self.statusbar.showMessage(self.current_status_message)
            self.recent_files_manager.add_file(filename)
            self.update_recent_files_menu()
            self.play_pause()
        else:
            self.statusbar.showMessage(f"Error: File {filename} not found")

    def play_pause(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        else:
            self.media_player.play()
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))

    def stop(self):
        self.media_player.stop()
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

    def skip_backward(self, ms=DEFAULT_SKIP_TIME):
        actual_position = self.media_player.position()
        self.media_player.setPosition(max(0, actual_position - ms))

    def skip_forward(self, ms=DEFAULT_SKIP_TIME):
        actual_position = self.media_player.position()
        self.media_player.setPosition(min(self.media_player.duration(), actual_position + ms))

    def decrease_volume(self, step):
        current_volume = self.audio_output.volume() * 100
        new_volume = max(0.0, current_volume - step)
        self.set_volume(new_volume)
        self.volume_slider.setValue(int(new_volume))

    def increase_volume(self, step):
        current_volume = self.audio_output.volume() * 100
        new_volume = min(100.0, current_volume + step)
        self.set_volume(new_volume)
        self.volume_slider.setValue(int(new_volume))

    def set_volume(self, volume):
        self.audio_output.setVolume(volume / 100)

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.audio_output.setMuted(self.is_muted)
        self.mute_button.setIcon(self.style().standardIcon(
            QStyle.StandardPixmap.SP_MediaVolumeMuted if self.is_muted
            else QStyle.StandardPixmap.SP_MediaVolume
        ))

    def set_playback_speed(self, speed):
        self.playback_speed = speed
        self.media_player.setPlaybackRate(self.playback_speed)

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.exit_fullscreen()
        else:
            self.showFullScreen()
            self.is_fullscreen = True
            self.hide_controls_timer.start(3000)

    def exit_fullscreen(self):
        self.showNormal()
        self.is_fullscreen = False
        self.show_controls()

    def hide_controls(self):
        if self.is_fullscreen:
            self.controls_widget.hide()
            self.menubar.hide()
            self.statusbar.hide()

    def show_controls(self):
        self.controls_widget.show()
        self.menubar.show()
        self.statusbar.show()

    def position_changed(self, position):
        self.progress_slider.setValue(position)
        self.update_time_label(position)

    def duration_changed(self, duration):
        self.progress_slider.setRange(0, duration)

    def set_position(self, position):
        self.media_player.setPosition(position)

    def update_time_label(self, position):
        duration = self.media_player.duration()
        if duration > 0:
            current_time = self.format_time(position)
            total_time = self.format_time(duration)
            self.time_label.setText(f"{current_time} / {total_time}")

    def format_time(self, ms):
        s = ms // 1000
        m = s // 60
        h = m // 60
        s = s % 60
        m = m % 60

        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        else:
            return f"{m}:{s:02d}"

    def handle_error(self):
        self.play_button.setEnabled(False)
        self.statusbar.showMessage(f"Error: {self.media_player.errorString()}")

    def mouseMoveEvent(self, event):
        if self.isFullScreen:
            self.show_controls()
            self.hide_controls_timer.start(3000)
        super().mouseMoveEvent(event)

    def quit_program(self):
        QApplication.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PQMP()
    window.show()
    sys.exit(app.exec())
