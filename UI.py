import sys
import cv2
import logging
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from datetime import datetime, timedelta
from threading import Timer

import time
import resources_rc

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler('car_control.log'),
                        logging.StreamHandler()
                    ])


class LogViewer(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Log Viewer")
        self.resize(500, 300)

        layout = QVBoxLayout()
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        layout.addWidget(self.log_text_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.load_log()

    def load_log(self):
        try:
            with open('car_control.log', 'r') as file:
                log_content = file.read()
                self.log_text_edit.setPlainText(log_content)
        except Exception as e:
            self.log_text_edit.setPlainText(f"Failed to load log file: {str(e)}")


class MyButton(QPushButton):
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            event.ignore()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.video_capture:
            self.video_capture.release()

    def stop(self):
        self.timer.stop()

    def start(self):
        self.timer.start(30)

    def set_video_source(self, video_source):
        self.stop()
        if self.video_capture:
            self.video_capture.release()
        self.video_source = video_source
        self.video_capture = cv2.VideoCapture(self.video_source)
        if not self.video_capture.isOpened():
            logging.error(f"Unable to open video source {self.video_source}")
        else:
            self.start()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Car Assistant")
        self.resize(700, 400)
        self.setFixedSize(700, 400)
        self.car_running = False
        self.speed = 0
        self.is_brake_pressed = False
        self.is_hard_braking = False

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        self.main_layout = QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)

        self.speed_lcd = QLCDNumber()
        self.speed_lcd.setDigitCount(3)
        self.speed_lcd.display(self.speed)
        self.speed_lcd.setFixedSize(100, 50)
        self.speed_lcd.setStyleSheet("background-color: black; color: red;")
        self.main_layout.addWidget(self.speed_lcd, alignment=Qt.AlignCenter)

        self.control_layout = QHBoxLayout()
        self.main_layout.addLayout(self.control_layout)

        self.turn_left_button = MyButton()
        left_icon = QIcon(QPixmap(r':/icon/turn_left.png'))
        self.turn_left_button.setIcon(left_icon)
        self.turn_left_button.setIconSize(QSize(100, 100))
        self.turn_left_button.setFixedSize(100, 100)
        self.turn_left_button.clicked.connect(self.turn_left)
        self.control_layout.addWidget(self.turn_left_button)

        self.turn_right_button = MyButton()
        right_icon = QIcon(QPixmap(r':/icon/turn_right.png'))
        self.turn_right_button.setIcon(right_icon)
        self.turn_right_button.setIconSize(QSize(100, 100))
        self.turn_right_button.setFixedSize(100, 100)
        self.turn_right_button.clicked.connect(self.turn_right)
        self.control_layout.addWidget(self.turn_right_button)

        # Adding Start and Stop buttons
        self.start_button = QPushButton("Start")
        self.start_button.setFixedSize(QSize(100, 25))
        self.start_button.clicked.connect(self.start_car)
        self.main_layout.addWidget(self.start_button, alignment=Qt.AlignCenter)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setFixedSize(QSize(100, 25))
        self.stop_button.clicked.connect(self.stop_car)
        self.main_layout.addWidget(self.stop_button, alignment=Qt.AlignCenter)

        self.view_box_button = MyButton("View Box")
        self.view_box_button.setFixedSize(QSize(100, 25))
        self.view_box_button.clicked.connect(self.view_box)
        self.main_layout.addWidget(self.view_box_button, alignment=Qt.AlignCenter)

        self.brake_button = MyButton()
        brake_icon = QIcon(QPixmap(r':/icon/brake.png'))
        self.brake_button.setIcon(brake_icon)
        self.brake_button.setIconSize(QSize(100, 100))
        self.brake_button.pressed.connect(self.brake_pressed)
        self.brake_button.released.connect(self.brake_released)
        self.main_layout.addWidget(self.brake_button, alignment=Qt.AlignCenter)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_buttons)
        self.timer.start(500)

        self.left_blinking = False
        self.right_blinking = False
        self.blink_state = False
        self.brake_blinking = False
        self.brake_just_clicked = False

        # Adding View Log button
        self.view_log_button = QPushButton("View Log")
        self.view_log_button.setFixedSize(QSize(100, 25))
        self.view_log_button.clicked.connect(self.view_log)
        self.main_layout.addWidget(self.view_log_button, alignment=Qt.AlignCenter)

        self.acceleration_timer = QTimer()
        self.acceleration_timer.timeout.connect(self.accelerate)
        self.deceleration_timer = QTimer()
        self.deceleration_timer.timeout.connect(self.decelerate)

    def view_box(self):
        if self.car_running:
            pass

    def turn_left(self):
        left = False
        if self.left_blinking:
            self.left_blinking = False
            self.log_status("Left off")
            left = False
            return left
        else:
            self.left_blinking = True
            if self.right_blinking:
                self.right_blinking = False
            self.log_status("Left on")
            left = True
            return left

    def turn_right(self):
        right = False
        if self.right_blinking:
            self.right_blinking = False
            self.log_status("Right off")
            right = False
            return right
        else:
            self.right_blinking = True
            if self.left_blinking:
                self.left_blinking = False
            self.log_status("Right on")
            right = True
            return right

    def brake_pressed(self):
        brake = False
        if self.car_running:
            self.log_status("Brake on")
            self.is_brake_pressed = True
            self.is_hard_braking = True
            self.acceleration_timer.stop()
            self.deceleration_timer.start(10)
            brake = True
            return brake
        else:
            brake = False
            self.log_status("Brake off")
            return brake

    def brake_released(self):
        if self.car_running:
            self.log_status("Brake released")
            self.is_brake_pressed = False
            self.is_hard_braking = False
            self.brake_blinking = False
            self.brake_just_clicked = True
            self.deceleration_timer.stop()
            self.acceleration_timer.start(100)

    def view_box(self):
        if self.car_running:
            pass

    def speedometer(self):
        if self.car_running:
            speed = self.current_speed  #
            self.speed_lcd.display(f"Speed: {speed} km/h")
            print(f"Speed: {speed} km/h")
            return speed
        else:
            self.speed_lcd.display("Car is not running")
            return 0

    def update_buttons(self):
        if self.car_running:
            self.blink_state = not self.blink_state

            if self.left_blinking:
                color = "lightgreen" if self.blink_state else ""
                self.turn_left_button.setStyleSheet(f"background-color: {color}")
            else:
                self.turn_left_button.setStyleSheet("")

            if self.right_blinking:
                color = "lightgreen" if self.blink_state else ""
                self.turn_right_button.setStyleSheet(f"background-color: {color}")
            else:
                self.turn_right_button.setStyleSheet("")

            if self.is_brake_pressed:
                self.brake_button.setStyleSheet("background-color: red")
            else:
                if self.brake_just_clicked:
                    self.brake_button.setStyleSheet("background-color: red")
                    self.brake_just_clicked = False
                else:
                    self.brake_button.setStyleSheet("")
        else:
            self.turn_left_button.setStyleSheet("")
            self.turn_right_button.setStyleSheet("")
            self.brake_button.setStyleSheet("")
            self.stop_car()

    def keyPressEvent(self, event):
        if self.car_running:
            if event.key() == Qt.Key_A:
                self.turn_left()
            elif event.key() == Qt.Key_D:
                self.turn_right()
            elif event.key() == Qt.Key_S:
                self.brake_pressed()

    def keyReleaseEvent(self, event):
        if self.car_running:
            if event.key() == Qt.Key_S:
                self.brake_released()

    def start_car(self):
        running = False
        logging.info("Car started")
        self.car_running = True
        self.acceleration_timer.start(100)
        if self.car_running:
            running = True
        else:
            running = False
        return running

    def stop_car(self):
        if self.car_running:
            self.car_running = False
            self.speed = 0
            self.speed_lcd.display(self.speed)
            logging.info("Car stopped")

    def decelerate(self):
        if self.speed > 0:
            self.speed -= 1
            self.speed_lcd.display(self.speed)
            self.log_status(f"Speed {self.speed} km/h")
            return self.speed

        else:
            self.deceleration_timer.stop()
            logging.info(f"Speed {self.speed} km/h")
            return self.speed

    def accelerate(self):
        if self.car_running and self.speed < 50:
            self.speed += 1
            self.speed_lcd.display(self.speed)
            self.log_status(f"Speed {self.speed} km/h")
            return self.speed
        else:
            self.acceleration_timer.stop()
            self.log_status(f"Speed {self.speed} km/h")
            return self.speed

    def log_status(self, action):
        log_message = (f"{action} - left({'on' if self.left_blinking == True else 'off'}) - "
                       f"right({'on' if self.right_blinking == True else 'off'}) - "
                       f"speed({self.speed} km/h) - "
                       f"brake({'on' if self.brake_pressed else 'off'})")
        logging.info(log_message)

    def view_log(self):
        log_viewer = LogViewer()
        log_viewer.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(r'Car_Driving_Assistance\icon\draftUI.png'))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
