from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QTabWidget,
    QGroupBox,
    QPushButton,
    QSpinBox,
    QLineEdit,
    QGridLayout,
)
from PySide6.QtCore import Qt
from theme import THEME


class SettingsCard(QGroupBox):
    def __init__(self, title, layout_class=QVBoxLayout, parent=None):
        super().__init__(title, parent)
        self.layout = layout_class(self)
        self.layout.setContentsMargins(10, 20, 10, 10)
        self.layout.setSpacing(10)
        self.setStyleSheet(f"""
            QGroupBox {{ 
                border: 1px solid {THEME["ui_secondary_border"]}; 
                border-radius: 8px; 
                margin-top: 15px; 
                font-weight: bold; 
                color: {THEME["highlighted_disabled"]}; 
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; color: {THEME["highlighted"]}; }}
        """)


class SettingsCheckbox(QCheckBox):
    def __init__(self, text, name, parent=None):
        super().__init__(text, parent)
        self.name = name
        # Initialize from runtime settings
        val = runtime.settings.get(name)
        self.setChecked(bool(val))
        self.stateChanged.connect(self._on_changed)
        self.setStyleSheet(f"""
            QCheckBox {{ color: {THEME["ui_text"]}; font-size: 14px; padding: 5px; }}
            QCheckBox:hover {{ color: {THEME["highlighted"]}; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {THEME["ui_secondary_border"]}; background: {THEME["ui_secondary"]}; border-radius: 4px; }}
            QCheckBox::indicator:hover {{ border: 1px solid {THEME["highlighted"]}; }}
            QCheckBox::indicator:checked {{ background: {THEME["highlighted"]}; border: 1px solid {THEME["highlighted"]}; }}
        """)

    def _on_changed(self, state):
        runtime.settings.set(self.name, state == Qt.Checked)


class SettingsNumericEntry(QWidget):
    def __init__(self, label, name, value, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(label)
        self.label.setFixedWidth(200)
        self.label.setStyleSheet(f"color: {THEME['ui_text']}; font-size: 14px;")

        self.spin = QSpinBox()
        self.spin.setValue(int(value))
        self.spin.setRange(0, 999)
        self.spin.setFixedWidth(60)
        self.spin.setStyleSheet(f"""
            QSpinBox {{
                background: {THEME["ui_secondary"]}; 
                border: 1px solid {THEME["ui_secondary_border"]}; 
                color: {THEME["ui_text"]}; 
                padding: 4px;
                border-radius: 4px;
            }}
            QSpinBox:hover {{
                border: 1px solid {THEME["highlighted"]};
                background: {THEME["ui_secondary_hover"]};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: {THEME["ui_secondary_hover"]};
                border: none;
                width: 16px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background: {THEME["highlighted_shadow"]};
            }}
        """)
        self.spin.valueChanged.connect(lambda val: runtime.settings.set(name, int(val)))

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.spin)
        self.layout.addStretch()


class SettingsTextEntry(QWidget):
    def __init__(self, label, name, value, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(label)
        self.label.setFixedWidth(200)
        self.label.setStyleSheet(f"color: {THEME['ui_text']}; font-size: 14px;")

        self.text = QLineEdit()
        self.text.setText(value)
        self.text.setFixedWidth(60)
        self.text.setStyleSheet(f"""
            QLineEdit {{
                background: {THEME["ui_secondary"]}; 
                border: 1px solid {THEME["ui_secondary_border"]}; 
                color: {THEME["ui_text"]}; 
                padding: 4px;
                border-radius: 4px;
            }}
            QLineEdit:hover {{
                border: 1px solid {THEME["highlighted"]};
                background: {THEME["ui_secondary_hover"]};
            }}
        """)
        self.text.textChanged.connect(lambda val: runtime.settings.set(name, val))

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.text)
        self.layout.addStretch()


class SettingsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(800, 650)
        self.setStyleSheet(
            f"#SettingsWindow {{ background-color: {THEME['ui_primary']}; }} QWidget {{ color: {THEME['ui_text']}; }}"
        )

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # We'll use a QTabWidget for the main categories
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {THEME["ui_secondary_border"]}; background: {THEME["ui_primary"]}; border-radius: 4px; }}
            QTabBar::tab {{ background: {THEME["ui_secondary"]}; padding: 12px 25px; border-right: 1px solid {THEME["ui_secondary_border"]}; border-bottom: 1px solid {THEME["ui_secondary_border"]}; color: {THEME["ui_text"]}; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }}
            QTabBar::tab:selected {{ background: {THEME["ui_primary"]}; border-bottom: 2px solid {THEME["highlighted"]}; color: {THEME["highlighted"]}; }}
            QTabBar::tab:hover:!selected {{ background: {THEME["ui_secondary_hover"]}; color: {THEME["highlighted"]}; }}
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
        self.btn_close.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {THEME["ui_secondary"]}; 
                border: 1px solid {THEME["ui_secondary_border"]}; 
                color: {THEME["ui_text"]};
                padding: 10px; 
                border-radius: 4px; 
                font-weight: bold; 
            }}
            QPushButton:hover {{ 
                background-color: {THEME["ui_secondary_hover"]}; 
                border: 1px solid {THEME["highlighted"]};
                color: {THEME["highlighted"]};
            }}
        """)
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
        layout = QGridLayout(tab)
        stats = SettingsCard("Stats")
        stats.layout.addWidget(SettingsTextEntry("Name", "Domme.name", runtime.settings.Domme.name))
        stats.layout.addWidget(SettingsNumericEntry("Age", "Domme.age", runtime.settings.Domme.age))
        stats.layout.addWidget(SettingsTextEntry("Honorific", "Domme.honorific", runtime.settings.Domme.honorific))
        stats.layout.addWidget(SettingsTextEntry("Short Name", "Domme.short_name", runtime.settings.Domme.short_name))
        layout.addWidget(stats, 0, 0)
        personality = SettingsCard("Personality", QGridLayout)
        personality.layout.addWidget(SettingsCheckbox("CFNM", "cfnm"), 0, 0)
        personality.layout.addWidget(SettingsCheckbox("Crazy", "crazy"), 0, 1)
        personality.layout.addWidget(SettingsCheckbox("Sadistic", "sadistic"), 1, 0)
        personality.layout.addWidget(SettingsCheckbox("Vulgar", "vulgar"), 1, 1)
        personality.layout.addWidget(SettingsCheckbox("Supremacist", "supremacist"), 2, 0)
        personality.layout.addWidget(SettingsCheckbox("Degrading", "degrading"), 2, 1)
        layout.addWidget(personality, 0, 1)

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
    from ui_qt import load_application_fonts

    app = QApplication(sys.argv)
    load_application_fonts()
    window = SettingsWindow()
    window.setObjectName("SettingsWindow")
    window.show()
    sys.exit(app.exec())
