import sys
from PySide6.QtWidgets import QApplication
from main import runtime
from ui_qt import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Initialize the new Qt UI
    window = MainWindow()
    window.setWindowTitle(f"TeaseAI - {runtime.settings.Sub.name}")
    window.show()
    
    # Optional: Initial background tasks could be started here via Bus.emit("start")
    
    sys.exit(app.exec())
