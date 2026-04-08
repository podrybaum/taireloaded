import os
import tkinter as tk
from editor_ui import RegistryEditor

if __name__ == "__main__":
    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root = tk.Tk()
    app = RegistryEditor(root, app_root)
    root.mainloop()
