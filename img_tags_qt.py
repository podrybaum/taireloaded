import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QCheckBox, QScrollArea, QGroupBox, QPushButton, QLineEdit,
    QFileDialog, QFrame
)
from PySide6.QtCore import Qt
from bus import Bus
from utils import is_image_file

class SectionGroupBox(QGroupBox):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 20, 10, 10)
        self.layout.setSpacing(5)
        self.setStyleSheet("""
            QGroupBox { 
                border: 1px solid #3d3d3d; 
                border-radius: 8px; 
                margin-top: 15px; 
                font-weight: bold; 
                color: #888; 
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #545454; }
            QCheckBox { color: #e0e0e0; font-size: 13px; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #333; border-radius: 3px; background: #222; }
            QCheckBox::indicator:checked { background: #3f51b5; border: 1px solid #3f51b5; }
        """)

class ImageTagger(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Tagger")
        self.resize(1100, 800)
        self.setStyleSheet("background-color: #000000; color: #e0e0e0;")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.tags = {} # Dict of {tag_id: QCheckBox}
        
        # Row 1: File Browser & Controls
        self._setup_controls()
        
        # Row 2: Scrollable Tagging area
        self._setup_tagging_area()
        
        self.imgs = []
        self.index = 0
        self.folder = ""
        self.tag_file = ""

    def _setup_controls(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        
        self.path_input = QLineEdit("Select images directory")
        self.path_input.setReadOnly(True)
        self.path_input.setStyleSheet("background: #1a1a1e; border: 1px solid #333; padding: 10px; border-radius: 5px;")
        
        self.btn_browse = QPushButton("Browse")
        self.btn_browse.setFixedWidth(100)
        self.btn_browse.clicked.connect(self._on_browse)
        self.btn_browse.setStyleSheet("QPushButton { background-color: #221e25; border: 1px solid #333; } QPushButton:hover { background-color: #332d36; }")
        
        self.btn_prev = QPushButton("<")
        self.btn_prev.setFixedWidth(40)
        self.btn_prev.clicked.connect(self._go_back)
        self.btn_prev.setStyleSheet("QPushButton { background-color: #221e25; border: 1px solid #333; }")
        
        self.lbl_progress = QLabel("0 / 0")
        self.lbl_progress.setFixedWidth(100)
        self.lbl_progress.setAlignment(Qt.AlignCenter)
        self.lbl_progress.setStyleSheet("font-weight: bold; color: #888;")
        
        self.btn_next = QPushButton(">")
        self.btn_next.setFixedWidth(40)
        self.btn_next.clicked.connect(self._go_forward)
        self.btn_next.setStyleSheet("QPushButton { background-color: #221e25; border: 1px solid #333; }")
        
        self.btn_exit = QPushButton("Finished")
        self.btn_exit.setFixedWidth(100)
        self.btn_exit.clicked.connect(self._save_and_exit)
        self.btn_exit.setStyleSheet("QPushButton { background-color: #225a22; border: 1px solid #333; } QPushButton:hover { background-color: #2d7a2d; }")
        
        row.addWidget(self.path_input)
        row.addWidget(self.btn_browse)
        row.addWidget(self.btn_prev)
        row.addWidget(self.lbl_progress)
        row.addWidget(self.btn_next)
        row.addWidget(self.btn_exit)
        self.main_layout.addLayout(row)

    def _setup_tagging_area(self):
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll_content = QWidget()
        self.grid = QGridLayout(self.scroll_content)
        self.grid.setSpacing(15)
        
        # Section 1: Category
        self._add_section("Category", [
            "Hardcore", "Lesbian", "Gay", "Bisexual", "Solo F", "Solo M", "Solo Futa",
            "POV", "Bondage", "S&M", "T&D", "Chastity", "CFNM", "Bath", "Shower", "Outdoors", "Artwork"
        ], 0, 0)
        
        # Section 2: Sex
        self._add_section("Sex", [
            "Masturbation", "Handjob", "Fingering", "Blowjob", "Cunnilingus", "Titjob", "Footjob",
            "Facesitting", "Rimming", "Missionary", "Doggystyle", "Cowgirl", "Reverse Cowgirl",
            "Standing", "Anal Sex", "DP", "Gangbang"
        ], 0, 1)
        
        # Section 3: Genders & Roles
        self._add_section("Genders & Roles", [
            "1 Woman", "2 Women", "3 Women", "1 Man", "2 Men", "3 Men", "1 Futa", "2 Futa", "3 Futa",
            "Femdom", "Maledom", "Futadom", "Femsub", "Malesub", "Futasub", "Multi-Dom", "Multi-Sub"
        ], 0, 2)
        
        # Section 4: Body Parts
        self._add_section("Body Parts", [
            "Face", "Fingers", "Mouth", "Tits", "Nipples", "Pussy", "Ass", "Legs", "Feet", "Cock", "Balls"
        ], 1, 0)
        
        # Section 5: Outfit
        self._add_section("Outfit", [
            "Nurse", "Teacher", "Schoolgirl", "Maid", "Superhero"
        ], 2, 0)
        
        # Section 6: BDSM
        self._add_section("BDSM", [
            "Whipping", "Spanking", "Cock Torture", "Ball Torture", "Strap-On", "Blindfold", "Gag", "Clamps", "Hot Wax", "Needles", "Electro"
        ], 1, 1)
        
        # Section 7: Misc
        self._add_section("Misc", [
            "TAI Domme", "Cumshot", "Cum Eating", "Kissing", "Tattoos", "Stockings", "Vibrator", "Dildo", "Pocket Pussy", "Anal Toy", "Watersports"
        ], 2, 1)
        
        # Section 8: Hentai/JAV Themes
        self._add_section("Hentai/JAV Themes", [
            "Shibari", "Body Writing", "Tentacles", "Trap", "Bukkake", "Gangoru", "Bakunyuu", "Mahou Shoujo", "Ahegao", "Monster Girl"
        ], 1, 2, row_span=2)
        
        self.scroll.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll)

    def _add_section(self, title, tags, row, col, row_span=1, col_span=1):
        group = SectionGroupBox(title)
        for tag_text in tags:
            cb = QCheckBox(tag_text)
            group.layout.addWidget(cb)
            # Create a consistent ID matching the original Kivy code's text.replace(" ", "")
            # Let's stick closer to `replace(" ", "")`
            self.tags[tag_text.replace(" ", "")] = cb
        self.grid.addWidget(group, row, col, row_span, col_span)

    def _on_browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Images Directory")
        if folder:
            self.folder = folder
            self.path_input.setText(folder)
            self.imgs = sorted([f for f in os.listdir(folder) if is_image_file(f)])
            if self.imgs:
                self.index = 0
                self.tag_file = os.path.join(folder, "ImageTags.txt")
                if not os.path.exists(self.tag_file):
                    with open(self.tag_file, "w"):
                        pass
                self._load_image()

    def _load_image(self):
        if not self.imgs:
            return
        img_path = os.path.join(self.folder, self.imgs[self.index])
        Bus.emit("show_image", img_path)
        self.lbl_progress.setText(f"{self.index+1} / {len(self.imgs)}")
        self._clear_tags()
        self._get_tags_from_file()

    def _go_forward(self):
        if not self.imgs:
            return
        self._write_tags_to_file()
        if self.index < len(self.imgs) - 1:
            self.index += 1
            self._load_image()

    def _go_back(self):
        if not self.imgs:
            return
        self._write_tags_to_file()
        if self.index > 0:
            self.index -= 1
            self._load_image()

    def _clear_tags(self):
        for cb in self.tags.values():
            cb.setChecked(False)

    def _get_tags_from_file(self):
        if not os.path.exists(self.tag_file):
            return
        with open(self.tag_file, "r") as f:
            for line in f:
                parts = line.split()
                if parts and parts[0] == self.imgs[self.index]:
                    for tag in parts[1:]:
                        if tag in self.tags:
                            self.tags[tag].setChecked(True)

    def _write_tags_to_file(self):
        if not self.imgs:
            return
        current_tags = [t for t, cb in self.tags.items() if cb.isChecked()]
        new_line = self.imgs[self.index] + " " + " ".join(current_tags) + "\n"
        
        lines = []
        if os.path.exists(self.tag_file):
            with open(self.tag_file, "r") as f:
                lines = f.readlines()
        
        replaced = False
        for i, line in enumerate(lines):
            if line.startswith(self.imgs[self.index]):
                if current_tags:
                    lines[i] = new_line
                else:
                    lines[i] = "\n" 
                replaced = True
                break
        
        if not replaced and current_tags:
            lines.append(new_line)
            
        with open(self.tag_file, "w") as f:
            f.writelines(lines)

    def _save_and_exit(self):
        self._write_tags_to_file()
        self.close()

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = ImageTagger()
    window.show()
    sys.exit(app.exec())
