import sys
from PySide6.QtWidgets import QApplication
from PySide6 import QtGui
from PySide6.QtCore import Qt
from ui import MainWindow
from interpreter import Interpreter


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication()
    runtime = Interpreter()
    QtGui.QFontDatabase.addApplicationFont("ui_resources/Nasalization Rg.otf")
    window = MainWindow()
    window.setWindowTitle(f"TeaseAI - {runtime.settings.current_personality}")
    window.show()

    # Optional: Initial background tasks could be started here via Bus.emit("start")

    sys.exit(app.exec())
