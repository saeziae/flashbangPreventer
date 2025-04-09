#!/usr/bin/env python3
import sys
import mss
import numpy as np
from PIL import Image
import time
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtWidgets import QApplication, QWidget

AREA_SIZE = 100  # Size of each detection area
SHADER_OPACITY = 120  # Opacity of the shader (0-255)


def calculate_brightness(image):
    """Calculate average brightness of an image"""
    width, height = image.size
    pixels = np.array(image.convert('RGB'))

    # Calculate perceived brightness using NumPy vectorization
    brightness = 0.299 * pixels[:, :, 0] + 0.587 * \
        pixels[:, :, 1] + 0.114 * pixels[:, :, 2]

    # Simple average instead of gaussian weights
    average_brightness = np.mean(brightness)

    return average_brightness


def screen_capture():
    """Capture the screen content"""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Primary monitor
        screenshot = sct.grab(monitor)
        img = Image.frombytes(
            "RGB", (screenshot.width, screenshot.height), screenshot.rgb)
        return img


def detect_bright_areas(image, threshold=180, block_size=(100, 100)):
    """Detect areas exceeding brightness threshold"""
    width, height = image.size
    bright_areas = []

    for x in range(0, width, block_size[0]):
        for y in range(0, height, block_size[1]):
            block = image.crop((x, y, x + block_size[0], y + block_size[1]))
            weighted_brightness = calculate_brightness(block)

            if weighted_brightness > threshold:
                bright_areas.append((x, y, weighted_brightness))

    return bright_areas


class OverlayWindow(QWidget):
    """Transparent window overlay for bright area detection"""

    def __init__(self):
        super().__init__()

        screen_resolution = QApplication.primaryScreen().availableGeometry()
        screen_width, screen_height = screen_resolution.width(), screen_resolution.height()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setGeometry(0, 0, screen_width, screen_height)

        self.bright_areas = []

        # Update timer (25 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_overlay)
        self.timer.start(1000//25)

    def update_overlay(self):
        img = screen_capture()
        # Create a mask of currently shaded areas
        pixels = np.array(img)
        for x, y, _ in self.bright_areas:
            # Compensate for the shading effect in brightness calculation
            block = pixels[y:y+AREA_SIZE, x:x+AREA_SIZE]
            # Reverse the shading effect (opacity 120 = ~47% darkness)
            block = block / (1 - SHADER_OPACITY / 255)
            pixels[y:y+AREA_SIZE, x:x+AREA_SIZE] = np.clip(block, 0, 255)

        # Convert back to PIL Image for detection
        img = Image.fromarray(pixels.astype('uint8'))

        # Detect bright areas
        self.bright_areas = detect_bright_areas(
            img, block_size=(AREA_SIZE, AREA_SIZE))
        self.update()

    def paintEvent(self, event):
        """Paint the overlay with detected bright areas"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor(0, 0, 0, SHADER_OPACITY)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)  # Remove outline

        for area in self.bright_areas:
            x, y, _ = area
            painter.drawRect(x, y, AREA_SIZE, AREA_SIZE)

        painter.end()


def main():
    app = QApplication(sys.argv)
    window = OverlayWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
