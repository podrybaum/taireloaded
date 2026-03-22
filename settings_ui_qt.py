from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, 
    QTabWidget, QGroupBox, QPushButton, QSpinBox
)
from PySide6.QtCore import Qt
from main import runtime

class SettingsCard(QGroupBox):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 20, 10, 10)
        self.layout.setSpacing(10)
        self.setStyleSheet("""
            QGroupBox { 
                border: 1px solid #3d3d3d; 
                border-radius: 8px; 
                margin-top: 15px; 
                font-weight: bold; 
                color: #545454; 
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #3f51b5; }
        """)

class SettingsCheckbox(QCheckBox):
    def __init__(self, text, name, parent=None):
        super().__init__(text, parent)
        self.name = name
        # Initialize from runtime settings
        val = runtime.settings.get(name)
        self.setChecked(bool(val))
        self.stateChanged.connect(self._on_changed)
        self.setStyleSheet("color: #e0e0e0; font-size: 14px; padding: 5px;")

    def _on_changed(self, state):
        runtime.settings.set(self.name, state == Qt.Checked)

class SettingsNumericEntry(QWidget):
    def __init__(self, label, name, value, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel(label)
        self.label.setFixedWidth(200)
        self.label.setStyleSheet("color: #e0e0e0; font-size: 14px;")
        
        self.spin = QSpinBox()
        self.spin.setValue(int(value))
        self.spin.setRange(0, 999)
        self.spin.setFixedWidth(60)
        self.spin.setStyleSheet("background: #222; border: 1px solid #333; color: white; padding: 2px;")
        self.spin.valueChanged.connect(lambda val: runtime.settings.set(name, int(val)))
        
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.spin)
        self.layout.addStretch()

class SettingsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(800, 650)
        self.setStyleSheet("background-color: #141419; color: #e0e0e0;")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # We'll use a QTabWidget for the main categories
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #333; background: #1a1a1e; }
            QTabBar::tab { background: #222; padding: 12px 25px; border-right: 1px solid #333; color: #888; }
            QTabBar::tab:selected { background: #1a1a1e; border-bottom: 2px solid #3f51b5; color: white; }
            QTabBar::tab:hover { background: #2a2a30; }
        """)
        self.layout.addWidget(self.tabs)
        
        self._setup_general_tab()
        self._setup_sub_tab()
        self._setup_domme_tab()
        self._setup_contacts_tab()
        
        # Close button at bottom
        self.btn_close = QPushButton("Apply & Close")
        self.btn_close.clicked.connect(self.close)
        self.btn_close.setFixedWidth(120)
        self.btn_close.setStyleSheet("QPushButton { background-color: #3f51b5; border: none; padding: 10px; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #5c6bc0; }")
        self.layout.addWidget(self.btn_close, alignment=Qt.AlignRight)

    def _setup_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        layout.addWidget(SettingsCheckbox("Allow Domme to delete local media?", "domme_delete"))
        layout.addWidget(SettingsCheckbox("Randomize order of image slideshows?", "randomize_slides"))
        layout.addWidget(SettingsCheckbox("Offline Mode - (disables URL files )", "offline_mode"))
        layout.addStretch()
        
        self.tabs.addTab(tab, "General")

    def _setup_sub_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Stats Card
        stats = SettingsCard("Stats")
        stats.layout.addWidget(SettingsNumericEntry("Age", "Sub.age", runtime.settings.Sub.age))
        stats.layout.addWidget(SettingsNumericEntry("Cock Size", "Sub.cock_size", runtime.settings.Sub.cock_size))
        layout.addWidget(stats)
        
        # Property Settings
        layout.addWidget(SettingsCheckbox("Owns a chastity device", "Sub.has_chastity"))
        layout.addWidget(SettingsCheckbox("Chastity device requires piercing", "Sub.chastity_piercing"))
        layout.addWidget(SettingsCheckbox("Chastity device has spikes", "Sub.chastity_spikes"))
        
        layout.addStretch()
        self.tabs.addTab(tab, "Sub")

    def _setup_domme_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Domme settings (Placeholder for Pass 2)"))
        layout.addStretch()
        self.tabs.addTab(tab, "Domme")

    def _setup_contacts_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Contacts settings (Placeholder for Pass 2)"))
        layout.addStretch()
        self.tabs.addTab(tab, "Contacts")

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())
