# Dice Volume Controller for Python 3.10
# Save this as dice_volume.py and run with Python 3.10

import sys
import random
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QHBoxLayout, QLabel, QWidget, QSlider, QComboBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPainter, QColor, QPen
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

class DiceWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 1
        self.rolling = False
        self.roll_frames = 0
        self.setMinimumSize(100, 100)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw dice background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRoundedRect(5, 5, self.width() - 10, self.height() - 10, 15, 15)
        
        # Draw dice border
        painter.setPen(QPen(QColor(80, 80, 80), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(5, 5, self.width() - 10, self.height() - 10, 15, 15)
        
        # Draw dots based on current value
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(40, 40, 40))
        
        dot_size = min(self.width(), self.height()) / 10
        
        # Calculate positions for dots
        w, h = self.width() - 20, self.height() - 20
        positions = {
            1: [(w/2 + 10, h/2 + 10)],
            2: [(w/4 + 10, h/4 + 10), (3*w/4 + 10, 3*h/4 + 10)],
            3: [(w/4 + 10, h/4 + 10), (w/2 + 10, h/2 + 10), (3*w/4 + 10, 3*h/4 + 10)],
            4: [(w/4 + 10, h/4 + 10), (3*w/4 + 10, h/4 + 10), 
                (w/4 + 10, 3*h/4 + 10), (3*w/4 + 10, 3*h/4 + 10)],
            5: [(w/4 + 10, h/4 + 10), (3*w/4 + 10, h/4 + 10), 
                (w/2 + 10, h/2 + 10),
                (w/4 + 10, 3*h/4 + 10), (3*w/4 + 10, 3*h/4 + 10)],
            6: [(w/4 + 10, h/4 + 10), (3*w/4 + 10, h/4 + 10), 
                (w/4 + 10, h/2 + 10), (3*w/4 + 10, h/2 + 10),
                (w/4 + 10, 3*h/4 + 10), (3*w/4 + 10, 3*h/4 + 10)]
        }
        
        for x, y in positions[self.value]:
            painter.drawEllipse(int(x - dot_size/2), int(y - dot_size/2), 
                                int(dot_size), int(dot_size))
    
    def set_value(self, value):
        self.value = value
        self.update()
        
    def start_rolling(self):
        self.rolling = True
        self.roll_frames = 0
        self.roll_timer = QTimer(self)
        self.roll_timer.timeout.connect(self.roll_animation)
        self.roll_timer.start(80)
        
    def roll_animation(self):
        self.roll_frames += 1
        self.value = random.randint(1, 6)
        self.update()
        
        if self.roll_frames >= 10:
            self.rolling = False
            self.roll_timer.stop()
            self.roll_finished()
    
    def roll_finished(self):
        # This will be connected to a function in the main window
        pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Dice Volume Controller")
        self.setMinimumSize(400, 500)
        
        # Get audio interface
        self.setup_audio()
        
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setAlignment(Qt.AlignCenter)
        
        # Title
        title_label = QLabel("Dice Volume Controller")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Dice widget
        self.dice = DiceWidget()
        self.dice.roll_finished = self.on_roll_finished
        main_layout.addWidget(self.dice)
        
        # Roll button
        self.roll_button = QPushButton("Roll Dice")
        self.roll_button.setFont(QFont("Arial", 14))
        self.roll_button.setMinimumHeight(50)
        self.roll_button.clicked.connect(self.roll_dice)
        main_layout.addWidget(self.roll_button)
        
        # Mode selection
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Absolute", "Incremental", "Percentage"])
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        main_layout.addLayout(mode_layout)
        
        # Application selection (simplified - just system volume for now)
        app_layout = QHBoxLayout()
        app_label = QLabel("Volume Control:")
        self.app_combo = QComboBox()
        self.app_combo.addItem("System Volume")
        app_layout.addWidget(app_label)
        app_layout.addWidget(self.app_combo)
        main_layout.addLayout(app_layout)
        
        # Volume slider for feedback
        slider_layout = QHBoxLayout()
        slider_label = QLabel("Current Volume:")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        current_vol = int(self.get_current_volume() * 100)
        self.volume_slider.setValue(current_vol)
        self.volume_slider.setEnabled(False)  # Just for display
        slider_layout.addWidget(slider_label)
        slider_layout.addWidget(self.volume_slider)
        self.volume_label = QLabel(f"{current_vol}%")
        slider_layout.addWidget(self.volume_label)
        main_layout.addLayout(slider_layout)
        
        # History
        self.history_label = QLabel("Roll History:")
        main_layout.addWidget(self.history_label)
        
        self.history_text = QLabel("")
        self.history_text.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.history_text.setWordWrap(True)
        main_layout.addWidget(self.history_text)
        
        # Set main widget
        self.setCentralWidget(main_widget)
        
        # Timer to periodically update volume display
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_volume_display)
        self.update_timer.start(1000)  # Update every second
    
    def setup_audio(self):
        try:
            self.devices = AudioUtilities.GetSpeakers()
            self.interface = self.devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self.volume = cast(self.interface, POINTER(IAudioEndpointVolume))
            print("Audio interface initialized successfully")
        except Exception as e:
            print(f"Error setting up audio: {e}")
            # Fallback - we'll use a mock volume interface
            self.volume = None
    
    def get_current_volume(self):
        try:
            if self.volume:
                # Get master volume level (ranges from 0.0 to 1.0)
                vol = self.volume.GetMasterVolumeLevelScalar()
                return vol
            else:
                return 0.5  # Default fallback
        except Exception as e:
            print(f"Error getting volume: {e}")
            return 0.5
    
    def set_volume(self, value):
        try:
            if self.volume:
                # Clamp volume between 0 and 1
                value = max(0, min(1, value))
                self.volume.SetMasterVolumeLevelScalar(value, None)
                print(f"Volume set to {value:.2f}")
            else:
                print(f"Would set volume to {value:.2f} (mock mode)")
            self.update_volume_display()
        except Exception as e:
            print(f"Error setting volume: {e}")
    
    def update_volume_display(self):
        try:
            current_vol = self.get_current_volume()
            self.volume_slider.setValue(int(current_vol * 100))
            self.volume_label.setText(f"{int(current_vol * 100)}%")
        except Exception as e:
            print(f"Error updating volume display: {e}")
    
    def roll_dice(self):
        self.roll_button.setEnabled(False)
        self.dice.start_rolling()
    
    def on_roll_finished(self):
        dice_value = self.dice.value
        current_volume = self.get_current_volume()
        new_volume = current_volume
        
        # Apply volume change based on selected mode
        mode = self.mode_combo.currentText()
        
        if mode == "Absolute":
            # Map dice value to volume levels: 1=0%, 2=20%, 3=40%, 4=60%, 5=80%, 6=100%
            new_volume = (dice_value - 1) / 5
        
        elif mode == "Incremental":
            # Each dice value changes volume differently:
            # 1: -25%, 2: -15%, 3: -5%, 4: +5%, 5: +15%, 6: +25%
            volume_change = (dice_value - 3.5) / 10
            new_volume = current_volume + volume_change
        
        elif mode == "Percentage":
            # Each dice value represents a percentage of full volume:
            # 1: 5%, 2: 20%, 3: 40%, 4: 60%, 5: 80%, 6: 100%
            percentages = {1: 0.05, 2: 0.2, 3: 0.4, 4: 0.6, 5: 0.8, 6: 1.0}
            new_volume = percentages[dice_value]
        
        # Apply the volume change
        self.set_volume(new_volume)
        
        # Update history
        history = self.history_text.text()
        history_entry = f"Rolled {dice_value}, Volume: {int(new_volume * 100)}%\n"
        self.history_text.setText(history_entry + history)
        
        # Re-enable roll button
        self.roll_button.setEnabled(True)


# Entry point of the application
if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error starting application: {e}")
        input("Press Enter to exit...")
