import json
import logging
import os
import pythoncom
import re
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, filedialog, Canvas, Scrollbar
from threading import Timer
from tkwebview2.tkwebview2 import WebView2
from typing import Dict, List
from dispatch import Dispatch

pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
logging.getLogger("pywebview").setLevel(logging.CRITICAL + 1)

# TODO: This thing is getting huge.  It's time for a refactor
# TODO: Sort the registry before outputting the dispatch dictionary
# TODO: Removing parameter rows doesn't work sometimes, figure that out.
# TODO: Make the delete key event handler only fire when focus is in the listbox
# TODO: Add traces to parameter row fields and integrate into the live preview
# TODO: Fix the "extra or" issue in the html generation logic
# TODO: Update the dispatch stub generator so it only generates stubs that don't already exist
#       and appends to the file rather than creating a new one.
# TODO: Dispatch stub generator needs to add =None to optional params.
# TODO: Wrap parameter info strings in table rows so they'll be formatted a little more nicely.
# TODO: Dispatch stub generator type hints?
# TODO: Unit test mapping, possibly unit test generation?
# TODO: Populate the return_value field for all entries.  We ended up not needing it, but it would
#       be good to have for unit tests.  Change its name to return_type
# TODO: In a perfect world before we save an entry we require:
#       docstring longer than (or equal length) whatever our current shortest docstring is
#       route to implementation  <- Implemented
#       implementing method exists in Dispatch  <- Currently checked when generating the dispatch dict.
#       return type specified
#       unit test exists/passes


def pre_init_webview():
    try:
        dummy_root = tk.Tk()
        dummy_root.withdraw()
        dummy_frame = ttk.Frame(dummy_root)
        dummy_frame.pack()
        dummy_web = WebView2(dummy_frame, width=1, height=1)
        dummy_web.load_html("<html><body></body></html>")
        dummy_web.update()
        dummy_frame.destroy()
        dummy_root.destroy()
    except Exception:
        pass  # We expect to get an exception here, so just swallow it.


pre_init_webview()


class Parameter:
    def __init__(self, type: str, optional: bool, description: str, position: int):
        self.position = position
        self.type = type
        self.optional = optional
        self.description = description

    def to_dict(self) -> dict:
        data = {
            "position": self.position,
            "type": self.type,
            "optional": self.optional,
            "description": self.description,
        }
        return data


class Command:
    def __init__(self):
        self.name: str = ""
        self.category: str = ""
        self.parameters: List[Parameter] = []
        self.description: str = ""
        self.deprecated_by: str = ""
        self.implemented_by: str = ""
        self.test_path: str = ""
        self.return_type: str = ""
        self.html_doc: str = ""
        self.syntax: str = ""

    def from_dict(self, data: dict):
        self.name = data.get("name", "")
        self.category = data.get("category", "")
        self.parameters = data.get("parameters", [])
        self.description = data.get("description", "")
        self.deprecated_by = data.get("deprecated_by", "")
        self.implemented_by = data.get("implemented_by", "")
        self.test_path = data.get("test_path", "")
        self.return_type = data.get("return_type", data.get("return_value", ""))
        self.html_doc = data.get("html_doc", "")
        self.syntax = data.get("syntax", "")

    def to_dict(self) -> dict:
        data = {
            "name": self.name,
            "category": self.category,
            "parameters": [param.to_dict() for param in self.parameters],
            "description": self.description,
            "deprecated_by": self.deprecated_by,
            "implemented_by": self.implemented_by,
            "test_path": self.test_path,
            "return_type": self.return_type,
            "html_doc": self.html_doc,
            "syntax": self.syntax,
        }
        return data


def get_html_header():
    with open("command_registry_header.html", "r", encoding="utf-8") as f:
        return f.read()


class RegistryEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("TAI Command Registry Editor")
        self.root.geometry("1324x768")
        self.param_rows = 0
        self.param_entries = []
        self.registry: Dict[str, Command] = {}
        self.current_entry: Command | None = None
        self.file = os.path.join(os.path.dirname(__file__), "command_registry.json")
        self.html_header = get_html_header()
        self.html_footer = "</body></html>"
        self._build_ui()
        self._refresh_listbox()
        self.name_entry.bind("<Tab>", self._copy_name_to_syntax, add="+")
        self.type_select_box.bind("<<ComboboxSelected>>", self._refresh_listbox, add="+")
        root.bind("<Return>", self._save_entry)
        root.bind("<Delete>", self._delete_command)
        self.status.set("Program initialized.")

        self._is_loading = False

        # auto import our file
        if os.path.isfile(self.file):
            self._import_json(self.file)

        # trigger auto save on close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    # Callbacks




    def _populate_syntax_for_command_filter(self, event=None):
        if (
            self.category_dropdown.get() == "Command Filter"
            or self.current_entry.category == "Command Filter"
            or self.category_var.get() == "Command Filter"
        ):
            name = self.name_var.get().strip()
            self.syntax_var.set(f"{name} Skip this line unless")

    def _on_closing(self):
        if self.registry:
            self._export_json(self.file)
        self.root.destroy()
        os._exit(0)

    def _copy_name_to_syntax(self, event=None):
        self.syntax.delete(0, tk.END)
        self.syntax.insert(0, self.name_entry.get())

    def _populate_or_disable_return(self, event=None):
        category = self.category_dropdown.get()
        if category == "Command Filter":
            self.return_dropdown.config(state="disabled")
            self.return_var.set("bool")
            self.return_dropdown.set("bool")
        elif category == "Command":
            self.return_dropdown.config(state="disabled")
            self.return_var.set("")
            self.return_dropdown.set("")
        elif category == "Keyword":
            self.return_dropdown.config(state="normal")
            self.return_var.set("string")

    def _open_docstring_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title(f"Edit Docstring: {self.name_var.get() or 'New Entry'}")
        popup.geometry("900x600")
        popup.transient(self.root)
        popup.grab_set()
        popup.resizable(True, True)
        text_frame = ttk.Frame(popup)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        text = tk.Text(text_frame, wrap="word", undo=True, font=("Consolas", 11))
        text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        scroll.pack(side="right", fill="y")
        text["yscrollcommand"] = scroll.set
        current_text = self.docstring_var.get()
        text.insert("1.0", current_text)
        text.mark_set("insert", "1.0")
        btn_frame = ttk.Frame(popup)
        btn_frame.pack(fill="x", pady=(0, 10), padx=10)

        def save_and_close():
            new_text = text.get("1.0", "end-1c").strip()
            self.docstring_var.set(new_text)
            self._update_preview()
            popup.destroy()

        def popup_enter(event):
            focused = popup.focus_get()
            if focused != text:
                save_and_close()

        popup.bind("<Return>", popup_enter)

        def insert_newline(event):
            text.insert("insert", "\n")
            return "break"

        text.bind("<Return>", insert_newline)

        save_btn = ttk.Button(btn_frame, text="Save & Close", command=save_and_close)
        save_btn.pack(side="right", padx=5)
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=popup.destroy)
        cancel_btn.pack(side="right", padx=5)
        popup.bind("<Escape>", lambda e: popup.destroy())
        text.focus_set()

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=10, takefocus=0)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.status = StatusBar(main_frame)
        self.status.pack(expand=False, fill=tk.X, side=tk.BOTTOM)

        # Left: list of commands
        list_frame = ttk.Frame(main_frame, takefocus=0)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))

        self.type_selector = tk.StringVar()
        self.type_select_box = ttk.Combobox(
            list_frame, textvariable=self.type_selector, values=("Commands", "Command Filters", "Keywords"), takefocus=0
        )
        self.type_select_box.pack(anchor="w", fill=tk.X, pady=2, padx=1)
        self.type_select_box.state(["readonly"])
        self.type_selector.set("Commands")
        self.cmd_listbox = tk.Listbox(list_frame, width=30, height=30, takefocus=0)
        self.cmd_listbox.pack(anchor="w", fill=tk.BOTH, expand=True)
        self.cmd_listbox.bind("<<ListboxSelect>>", self._on_select_command)

        btn_frame = ttk.Frame(list_frame, takefocus=0)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="New", command=self._new_command, takefocus=0).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Copy", command=self._copy_command, takefocus=0).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Delete", command=self._delete_command, takefocus=0).pack(side=tk.LEFT)

        # Right: editor form
        self.editor_frame = ttk.LabelFrame(main_frame, text="Edit Entry", padding=10, takefocus=0)
        self.editor_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Name
        ttk.Label(self.editor_frame, text="Name:", takefocus=0).grid(row=0, column=0, sticky="w", pady=2)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(self.editor_frame, textvariable=self.name_var, width=50)
        self.name_entry.grid(row=0, column=1, sticky="w", pady=2, padx=5)
        self.name_var.trace("w", lambda *args: self._update_preview())

        # Deprecated
        ttk.Label(self.editor_frame, text="Deprecated by:", takefocus=0).grid(
            row=0, column=2, sticky="e", pady=2, padx=5
        )
        self.deprecated_var = tk.StringVar()
        self.deprecated_entry = ttk.Entry(self.editor_frame, textvariable=self.deprecated_var, width=50)
        self.deprecated_entry.grid(row=0, column=3, sticky="w", pady=2)
        self.deprecated_var.trace("w", lambda *args: self._update_preview())

        # Category
        ttk.Label(self.editor_frame, text="Category:", takefocus=0).grid(row=1, column=0, sticky="w", pady=2)
        self.category_var = tk.StringVar()
        self.category_dropdown = ttk.Combobox(
            self.editor_frame,
            textvariable=self.category_var,
            values=("Command", "Command Filter", "Keyword"),
            takefocus=0,
            width=47,
        )
        self.category_var.set("Command")
        self.category_dropdown.state(["readonly"])
        self.category_dropdown.grid(row=1, column=1, sticky="w", pady=2, columnspan=1, padx=5)
        self.category_var.trace("w", lambda *args: self._update_preview())
        self.category_dropdown.bind("<<ComboboxSelected>>", self._populate_syntax_for_command_filter, add="+")
        self.category_dropdown.bind("<<ComboboxSelected>>", self._populate_or_disable_return, add="+")

        # Return type

        ttk.Label(self.editor_frame, text="Return Type:", takefocus=0).grid(row=2, column=0, sticky="w", pady=2)
        self.return_var = tk.StringVar()
        self.return_dropdown = ttk.Combobox(
            self.editor_frame, textvariable=self.return_var, values=("int", "string"), takefocus=0, width=47
        )
        self.return_var.set("string")
        self.return_dropdown.state(["readonly"])
        self.return_dropdown.grid(row=2, column=1, sticky="w", pady=2, columnspan=1, padx=5)

        # Implemented
        ttk.Label(self.editor_frame, text="Implemented by:", takefocus=0).grid(
            row=1, column=2, sticky="e", pady=2, padx=5
        )
        self.implemented_var = tk.StringVar()
        self.implemented_entry = ttk.Entry(self.editor_frame, textvariable=self.implemented_var, width=50)
        self.implemented_entry.grid(row=1, column=3, sticky="w", pady=2)

        # Test Path
        ttk.Label(self.editor_frame, text="Test Path:", takefocus=0).grid(row=2, column=2, sticky="e", pady=2, padx=5)
        test_path_frame = ttk.Frame(self.editor_frame)
        test_path_frame.grid(row=2, column=3, sticky="w", pady=2)
        self.test_path_var = tk.StringVar()
        self.test_path_entry = ttk.Entry(test_path_frame, textvariable=self.test_path_var, width=39)
        self.test_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(test_path_frame, text="Browse", width=8, command=self._browse_test_path, takefocus=0).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        # Parameters
        self.param_frame = ttk.LabelFrame(self.editor_frame, text="Parameters", takefocus=0)
        self.param_frame.grid(row=3, column=0, sticky="nsew", pady=2, columnspan=4)
        self.param_frame.columnconfigure(0, weight=1)
        self.param_frame.rowconfigure(0, weight=1)
        self.param_inputs_frame = ttk.Frame(self.param_frame, takefocus=0)
        self.param_inputs_frame.grid(row=0, column=0, sticky="nsew", columnspan=4)
        ttk.Label(self.param_inputs_frame, text="Position:", takefocus=0).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Label(self.param_inputs_frame, text="Type:", takefocus=0).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(self.param_inputs_frame, text="Optional:", takefocus=0).grid(row=0, column=2, padx=5)
        ttk.Label(self.param_inputs_frame, text="Desc:", takefocus=0).grid(row=0, column=3, sticky="ew", padx=(5, 0))
        self.param_inputs_frame.columnconfigure(3, weight=1)
        self.add_param_button = ttk.Button(
            self.param_frame, text="Add Parameter", command=self._add_parameter, takefocus=0
        )
        self.add_param_button.grid(row=1, column=0, sticky="sw")

        # Docstring
        self.docstring_var = tk.StringVar()
        docstring_frame = ttk.LabelFrame(self.editor_frame, text="Docstring", takefocus=0)
        docstring_frame.grid(row=4, column=0, sticky="new", pady=2, columnspan=4)
        docstring_frame.grid_columnconfigure(0, weight=1)
        self.doc_text = tk.Entry(docstring_frame, textvariable=self.docstring_var)
        self.doc_text.grid(row=0, column=0, sticky="ew", padx=2, pady=2)

        # Small edit button on the right
        edit_btn = ttk.Button(docstring_frame, text="...", width=3, command=self._open_docstring_popup)
        edit_btn.grid(row=0, column=1, padx=(5, 2), sticky="e")
        self.docstring_var.trace("w", lambda *args: self._update_preview())

        # Syntax Example
        self.syntax_var = tk.StringVar()
        syntax_frame = ttk.LabelFrame(self.editor_frame, text="Syntax Example", takefocus=0)
        syntax_frame.grid(row=5, column=0, sticky="new", pady=2, columnspan=4)
        self.syntax = tk.Entry(syntax_frame, textvariable=self.syntax_var)
        self.syntax.pack(fill=tk.X, anchor="n", expand=True, padx=2, pady=2)
        self.syntax_var.trace("w", lambda *args: self._update_preview())

        # Preview
        preview_container = ttk.Frame(self.editor_frame)
        preview_container.grid(row=6, column=0, sticky="nsew", pady=2, columnspan=4)
        preview_container.grid_rowconfigure(0, weight=1)
        preview_container.grid_columnconfigure(0, weight=1)
        
        self.preview_web = WebView2(preview_container, takefocus=0, width=500, height=500)
        self.preview_web.grid(row=0, column=0, sticky="nsew", pady=(10, 0))
        
        bottom_frame = ttk.Frame(self.editor_frame, takefocus=0)
        bottom_frame.grid(row=7, column=0, sticky="sew", pady=2, columnspan=4)

        # Export/import buttons

        ttk.Button(bottom_frame, text="Save Entry", command=self._save_entry, takefocus=0).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="Export JSON", command=self._export_json, takefocus=0).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="Import JSON", command=self._import_json, takefocus=0).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="Generate Dispatch Dict", command=self._generate_dispatch, takefocus=0).pack(
            side=tk.RIGHT, padx=5
        )
        ttk.Button(bottom_frame, text="Generate HTML Docs", command=self._generate_docs, takefocus=0).pack(
            side=tk.RIGHT, padx=5
        )
        ttk.Button(
            bottom_frame, text="Generate Dispatch class stub", command=self.generate_dispatch_class_stub, takefocus=0
        ).pack(side=tk.RIGHT, padx=5)

        self.editor_frame.columnconfigure(1, weight=1)
        self.editor_frame.columnconfigure(3, weight=1)
        self.editor_frame.rowconfigure(6, weight=1)
        self.editor_frame.rowconfigure(7, weight=0)

    def _generate_dispatch(self):
        dropped_commands = []
        valid_registry = {}

        filepath = os.path.join(os.path.dirname(__file__), "dispatch.py")
        stubbed_methods = set()
        if os.path.isfile(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            current_method = None
            for line in lines:
                if line.strip().startswith("def "):
                    current_method = line.split("def ")[1].split("(")[0].strip()
                elif current_method and "pass" in line and "TODO" in line:
                    stubbed_methods.add(current_method)

        def resolves_to_implementation(cmd_name_full, visited=None):
            cmd_name = cmd_name_full.split("(")[0].strip()
            if visited is None:
                visited = set()
            if cmd_name in visited:
                return False, "Circular deprecated_by reference"
            visited.add(cmd_name)

            if cmd_name not in self.registry:
                return False, f"deprecated_by target '{cmd_name}' not found in registry"

            entry = self.registry[cmd_name]
            if entry.implemented_by:
                try:
                    if getattr(Dispatch, entry.implemented_by):
                        return True, ""
                except AttributeError:
                    return False, f"Method {entry.implemented_by} not found in Dispatch"
            elif entry.deprecated_by:
                return resolves_to_implementation(entry.deprecated_by, visited)

            return False, f"Command '{cmd_name}' has neither implemented_by nor deprecated_by"

        for name, entry in self.registry.items():
            if entry.deprecated_by:
                valid, reason = resolves_to_implementation(entry.deprecated_by, {name})
                if not valid:
                    dropped_commands.append((name, f"Invalid deprecated_by route: {reason}"))
                    continue
            else:
                # Check implementation
                if not entry.implemented_by:
                    dropped_commands.append((name, "No implementing_method or deprecated_by specified"))
                    continue

                if entry.implemented_by in stubbed_methods:
                    dropped_commands.append((name, f"Method {entry.implemented_by} is an unfinished stub"))
                    continue

                try:
                    if not getattr(Dispatch, entry.implemented_by):
                        dropped_commands.append((name, f"Method {entry.implemented_by} not found in Dispatch"))
                        continue
                except AttributeError:
                    dropped_commands.append((name, f"Method {entry.implemented_by} not found in Dispatch"))
                    continue

            # Check documentation
            if not entry.description or len(entry.description.strip()) < 10:
                dropped_commands.append((name, "Docstring too short (minimum 10 characters)"))
                continue

            # Check tests
            if not entry.test_path:
                dropped_commands.append((name, "No test path specified"))
                continue

            full_test_path = os.path.join(os.path.dirname(__file__), entry.test_path)
            if not os.path.exists(full_test_path):
                dropped_commands.append((name, f"Test path does not exist: {entry.test_path}"))
                continue

            if os.path.isdir(full_test_path):
                has_py_file = any(
                    f.endswith(".py")
                    for f in os.listdir(full_test_path)
                    if os.path.isfile(os.path.join(full_test_path, f))
                )
                if not has_py_file:
                    dropped_commands.append((name, f"Test directory {entry.test_path} contains no .py files"))
                    continue
            elif not full_test_path.endswith(".py"):
                dropped_commands.append((name, f"Test file {entry.test_path} must be a .py file"))
                continue

            valid_registry[name] = entry

        if dropped_commands:
            lines = [f"{name}: {reason}" for name, reason in dropped_commands]
            msg = f"Dropped {len(dropped_commands)} commands due to missing requirements:\n\n"
            msg += "\n".join(lines[:20])
            if len(lines) > 20:
                msg += f"\n...and {len(lines) - 20} more."
            msg += "\n\nDo you want to continue generating the dispatch dict without these commands?"
            if not messagebox.askyesno("Commands Dropped", msg):
                return

        dispatch_dict = {
            name: {
                "deprecated_by": entry.deprecated_by,
                "implemented_by": entry.implemented_by,
                "category": entry.category,
                "parameters": [{k: p.to_dict()[k] for k in ("type", "position", "optional")} for p in entry.parameters],
            }
            for name, entry in sorted(valid_registry.items())
        }

        for v in dispatch_dict.values():
            if v["implemented_by"] != "":
                v["implemented_by"] = f"Dispatch.{v['implemented_by']}"

        with open("dispatch_dict.py", "w", encoding="utf-8") as f:
            f.write("DISPATCH_DICT = {\n")
            for k, v in dispatch_dict.items():
                f.write(f"    '{k}': {v},\n")
            f.write("}\n")
        with open("dispatch_dict.py", "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            line = re.sub(r"\'Dispatch\.(\w+)\'", r"Dispatch.\1", line)
        with open("dispatch_dict.py", "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line)
        messagebox.showinfo("Generated", "Saved to dispatch_dict.py")

    def _generate_docs(self):
        self.status.set("Building docs...")

        for k, v in self.registry.items():
            v.html_doc = self.regenerate_html_doc(k)
        with open("docs.html", "w", encoding="utf-8") as f:
            f.write(self.html_header)
            for k in sorted(self.registry.keys()):
                f.write(f"{self.registry[k].html_doc}<br>")
                f.write("\n")
            f.write(self.html_footer)
            messagebox.showinfo("Generated", "Saved to docs.html")

    def _update_preview(self):
        if getattr(self, "_is_loading", False):
            return

        try:
            html = self.html_header
            html += f"""{self.generate_html_doc(self.name_var.get().strip())}"""
            html += self.html_footer

            self.preview_web.load_html(html)
            self.preview_web.update()  # Force the webview to repaint
            self.root.update_idletasks()
        except Exception:
            pass

    def _add_parameter(self):
        self.param_rows += 1
        position_var = tk.IntVar()
        position_entry = tk.Entry(self.param_inputs_frame, textvariable=position_var, width=2)
        position_entry.grid(row=self.param_rows, column=0, padx=5)
        type_var = tk.StringVar(self.param_frame)
        type_var.set("string")
        type_dropdown = ttk.OptionMenu(
            self.param_inputs_frame, type_var, "string", "string", "int", "*string", "*int", "bool"
        )
        type_dropdown.grid(row=self.param_rows, column=1, padx=5)
        optional_var = tk.BooleanVar()
        check = ttk.Checkbutton(self.param_inputs_frame, variable=optional_var)
        check.grid(row=self.param_rows, column=2, padx=5)
        desc_var = tk.StringVar()
        desc_entry = tk.Entry(self.param_inputs_frame, textvariable=desc_var, width=30)
        desc_entry.grid(row=self.param_rows, column=3, padx=(5, 0), sticky="ew")

        remove_btn = ttk.Button(self.param_inputs_frame, text="X", width=2)
        remove_btn.grid(row=self.param_rows, column=4, padx=5, sticky="e")
        remove_btn.config(command=lambda btn=remove_btn: self._remove_parameter_row(btn.grid_info()["row"]))

        # Add traces for live HTML preview
        type_var.trace("w", lambda *args: self._update_preview())
        optional_var.trace("w", lambda *args: self._update_preview())
        desc_var.trace("w", lambda *args: self._update_preview())
        position_var.trace("w", lambda *args: self._update_preview())

        self.param_entries.append(
            (
                self.param_rows,
                position_entry,
                type_dropdown,
                check,
                desc_entry,
                remove_btn,
                position_var,
                type_var,
                optional_var,
                desc_var,
            )
        )

    def _remove_parameter_row(self, row_to_remove):
        # Find and destroy all widgets in that row
        for widget in self.param_inputs_frame.winfo_children():
            info = widget.grid_info()
            if info and info["row"] == row_to_remove:
                widget.destroy()

        # Remove from tracking list
        self.param_entries = [r for r in self.param_entries if r[0] != row_to_remove]

        # Re-grid remaining rows to close the gap (shift rows up)
        new_rows = []
        current_row = 1  # start after header
        for old_row_data in self.param_entries:
            (_, pos_entry, type_dropdown, check, desc_entry, remove_btn, pos_var, type_var, optional_var, desc_var) = (
                old_row_data
            )

            # Move widgets to new row
            pos_entry.grid(row=current_row, column=0, padx=5)
            type_dropdown.grid(row=current_row, column=1, padx=5)
            check.grid(row=current_row, column=2, padx=5)
            desc_entry.grid(row=current_row, column=3, padx=(5, 0), sticky="ew")
            remove_btn.grid(row=current_row, column=4, padx=5, sticky="e")

            # Update stored row number
            new_rows.append(
                (
                    current_row,
                    pos_entry,
                    type_dropdown,
                    check,
                    desc_entry,
                    remove_btn,
                    pos_var,
                    type_var,
                    optional_var,
                    desc_var,
                )
            )

            current_row += 1

        self.param_entries = new_rows

    def _refresh_listbox(self, event=None):
        scroll_fraction = self.cmd_listbox.yview()[0]
        self.cmd_listbox.delete(0, tk.END)
        for name in sorted(self.registry.keys()):
            if self.registry[name].category == self.type_selector.get().rstrip("s"):
                self.cmd_listbox.insert(tk.END, name)
        self.cmd_listbox.yview_moveto(scroll_fraction)

    def _on_select_command(self, event):
        selection = self.cmd_listbox.curselection()
        if not selection:
            return
        name = self.cmd_listbox.get(selection[0])
        self.current_entry = self.registry.get(name)
        self._update_ui_from_entry()

    def _update_ui_from_entry(self):
        self._is_loading = True

        for widget in self.param_inputs_frame.winfo_children():
            widget.destroy()
        self.param_entries = []
        self.param_rows = 0

        self._populate_or_disable_return()

        for param in self.current_entry.parameters:
            self._add_parameter()
            _, _, _, _, _, _, pos_v, type_v, opt_v, desc_v = self.param_entries[-1]
            pos_v.set(param.position)
            type_v.set(param.type)
            opt_v.set(param.optional)
            desc_v.set(param.description)

        self.name_var.set(self.current_entry.name)
        self.deprecated_var.set(self.current_entry.deprecated_by)
        self.category_var.set(self.current_entry.category)
        if self.category_var.get() == "Command Filter":
            self.return_var.set("bool")
        if self.category_var.get() == "Command":
            self.return_var.set("")
        else:
            self.return_var.set(self.current_entry.return_type)
        self.docstring_var.set(self.current_entry.description)
        self.syntax_var.set(self.current_entry.syntax)
        self.implemented_var.set(self.current_entry.implemented_by)
        self.test_path_var.set(self.current_entry.test_path)

        self._is_loading = False
        self._update_preview()

    def _browse_test_path(self):
        path = filedialog.askopenfilename(
            title="Select Test Script",
            filetypes=[("Python Files", "*.py")],
            initialdir=os.path.join(os.path.dirname(__file__), "tests", "commands"),
        )
        if not path:
            path = filedialog.askdirectory(
                title="Select Test Folder", initialdir=os.path.join(os.path.dirname(__file__), "tests", "commands")
            )
        if path:
            try:
                # Try to store a relative path to keep the registry portable
                rel_path = os.path.relpath(path, os.path.dirname(__file__))
                self.test_path_var.set(rel_path)
            except ValueError:
                self.test_path_var.set(path)

    def _new_command(self):
        self.current_entry = Command()
        self._update_ui_from_entry()

    def _copy_command(self):
        self.name_var.set(self.current_entry.name + "_copy")
        self._save_entry()
        self._update_ui_from_entry()

    def _save_entry(self, event=None):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        if not self.docstring_var.get().strip():
            messagebox.showerror("Error", "Docstring is required!")
            return

        deprecated = self.deprecated_var.get().strip()
        implemented = self.implemented_var.get().strip()
        if deprecated != "" and deprecated is not None:
            if implemented is not None and implemented != "":
                messagebox.showerror("Error", "You must populate 'deprecated by' or 'implemented by', not both.")
                return

        if self.current_entry is None or self.current_entry.name != name:
            self.current_entry = Command()

        # Collect parameters from UI **first**
        new_params = []
        for row in self.param_entries:
            try:
                pos = row[6].get()
            except tk.TclError:
                pos = 0
            type = row[7].get()
            optional = row[8].get()
            desc = row[9].get()
            param = Parameter(type, optional, desc, pos)
            new_params.append(param)

        self.status.set(f"Record {name} saved.")

        # Now save everything
        self.current_entry.name = name
        self.current_entry.category = self.category_var.get().strip()
        self.current_entry.description = self.docstring_var.get().strip()
        self.current_entry.syntax = self.syntax_var.get().strip()
        self.current_entry.deprecated_by = self.deprecated_var.get().strip()
        self.current_entry.implemented_by = self.implemented_var.get().strip()
        self.current_entry.test_path = self.test_path_var.get().strip()
        self.current_entry.return_type = self.return_var.get()
        self.current_entry.parameters = new_params  # ← assign the collected objects
        self.current_entry.html_doc = self.generate_html_doc(name)

        # self.generate_html_doc(name)
        key = name
        self.registry[key] = self.current_entry

        self._refresh_listbox()
        self._update_preview()

    def regenerate_html_doc(self, name):
        docstring = self.registry[name].description
        docstring = self._link_commands(docstring)
        deprecated = self.registry[name].deprecated_by
        syntax = self.registry[name].syntax

        params = self.registry[name].parameters

        return self.get_html(name, docstring, deprecated, syntax, params)

    def get_html(self, name, docstring, deprecated, syntax, params):
        params_by_pos = [[]]
        for param in params:
            while len(params_by_pos) - 1 < param.position:
                params_by_pos.append([])
            params_by_pos[param.position].append(param)

        html = f"""<div class="entry" id="{name.lstrip("@").lstrip("#").lower()}_entry">"""
        # Command Name
        html += f"""<span id="{name.lstrip("@").lstrip("#").lower()}" class="cname">{name}"""

        # Parameter signature
        if len(params) > 0:
            html += """</span><span class="parens">(</span>"""
        param_str = ""
        for i, param_pos in enumerate(params_by_pos):
            if len(param_pos) == 1:
                param_str += (
                    f"""<span class="param_name" title="{param_pos[0].description}">{param_pos[0].type}</span>"""
                )
            # now handle multiple params in same pos
            else:
                types_html = []
                for param in param_pos:
                    types_html.append(f'<span class="param_name" title="{param.description}">{param.type}</span>')
                param_str += '<span class="param_desc"> or </span>'.join(types_html)
            param_str += ", " if i < len(params_by_pos) - 1 else ""
        html += param_str
        if len(params) > 0:
            html += '<span class="parens">)'
            html += "<br>"
        html += "</span>"
        # Params list
        if len(params) > 0:
            html += """<table class="param_table">"""
            for param_pos in params_by_pos:
                for i, param in enumerate(param_pos):
                    html += "<tr>"
                    if i == 0:
                        html += f"""<td class="list_param_pos" style="vertical-align: top;">Position: {param.position + 1} </td>"""
                    else:
                        html += """<td class="list_param_pos"></td>"""
                    html += f"""<td class="list_param_name" style="vertical-align: top; white-space: nowrap;">{param.type} """
                    if param.optional:
                        html += """ <span class="param_parens">(</span><span class="param_desc">optional</span><span class="param_parens">)</span> """
                    html += """</td>"""
                    html += f"""<td class="param_desc" style="vertical-align: top;"> - {param.description}</td>"""
                    html += "</tr>"
            html += """</table>"""

        # Syntax Examples
        html += f"""<br><code class="syntax">{syntax}</code>"""

        # Docstring
        html += f"""<p class="docs">{docstring}</p>"""

        # Deprecated by
        if deprecated not in [None, "", "None"]:
            html += f"""<span class="deprecated">&nbsp;Deprecated by: {self._link_deprecated_by(deprecated)}</span>"""
        html += """</div>"""

        return html

    def generate_html_doc(self, name):
        docstring = self.docstring_var.get().strip()
        docstring = self._link_commands(docstring)
        deprecated = self.deprecated_var.get().strip()
        syntax = self.syntax_var.get().strip()

        params = []
        for row in self.param_entries:
            try:
                pos = row[6].get()
            except tk.TclError:
                pos = 0
            type = row[7].get()
            optional = row[8].get()
            desc = row[9].get()
            param = Parameter(type, optional, desc, pos)
            params.append(param)

        return self.get_html(name, docstring, deprecated, syntax, params)

    def _link_deprecated_by(self, text: str) -> str:
        def repl(match):
            cmd = match.group(1)
            anchor = cmd.lower().replace("@", "").replace("#", "")
            return f'<a href="#{anchor}" title="Jump to {cmd}" style="color: #7af;">{cmd}</a><span>'

        hidden_tags = []

        def hide(match):
            hidden_tags.append(match.group(0))
            return f"__HIDDEN_A_{len(hidden_tags) - 1}__"

        text = re.sub(r"<a\b[^>]*>.*?</a>", hide, text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"([@#][a-zA-Z0-9]+)", repl, text, flags=re.IGNORECASE)
        for i, tag in enumerate(hidden_tags):
            text = text.replace(f"__HIDDEN_A_{i}__", tag)
        return text

    def _link_commands(self, text: str) -> str:
        def repl(match):
            cmd = match.group(1)
            if cmd.startswith("@Chance") and len(cmd) > 7:
                return cmd
            if cmd.startswith("#RandomRound") and len(cmd) > 12:
                return cmd
            if cmd.startswith("@FollowUp") and len(cmd) > len("@FollowUp"):
                return cmd
            anchor = cmd.lower().replace("@", "").replace("#", "")
            return f'<a href="#{anchor}" title="Jump to {cmd}" style="color: #7af;">{cmd}</a>'

        hidden_tags = []

        def hide(match):
            hidden_tags.append(match.group(0))
            return f"__HIDDEN_A_{len(hidden_tags) - 1}__"

        text = re.sub(r"<a\b[^>]*>.*?</a>", hide, text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"([@#]\w+)", repl, text, flags=re.IGNORECASE)
        for i, tag in enumerate(hidden_tags):
            text = text.replace(f"__HIDDEN_A_{i}__", tag)
        return text

    def _delete_command(self, event=None):
        if event is not None and self.root.focus_get() != self.cmd_listbox:
            return
        if not self.current_entry or not self.current_entry.name:
            return
        key = self.current_entry.name
        if messagebox.askyesno("Confirm", f"Delete {self.current_entry.name}?"):
            if key in self.registry:
                del self.registry[key]
            self.current_entry = Command()
            self._update_ui_from_entry()
            self._refresh_listbox()

    def _import_json(self, path=None):
        if path is None:
            path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], title="Open Registry JSON")
        if not path:
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "commands" not in data:
            messagebox.showerror("Error", "Invalid registry file: missing 'commands' key")
            return

        self.registry.clear()
        self.current_entry = None
        for name, cmd_data in data["commands"].items():
            cmd = Command()
            cmd.from_dict(cmd_data)
            params_data = cmd_data.get("parameters", [])
            cmd.parameters = []
            for p_data in params_data:
                param = Parameter(
                    type=p_data.get("type", "string"),
                    optional=p_data.get("optional", False),
                    description=p_data.get("description", ""),
                    position=p_data.get("position"),
                )
                cmd.parameters.append(param)
            self.registry[name] = cmd

        self._refresh_listbox()
        messagebox.showinfo("Imported", f"Loaded {len(self.registry)} entries from {path}")

    def _export_json(self, file=None):
        if not self.registry:
            messagebox.showwarning("Nothing to export", "Add some entries first")
            return
        if file is None:
            path = filedialog.asksaveasfilename(
                initialfile=self.file, filetypes=[("JSON files", "*.json")], title="Save Registry JSON"
            )
        else:
            path = file
        if not path:
            return
        data = {
            "version": "1.0.0",
            "generated": datetime.now().isoformat(),
            "commands": {k: self.registry[k].to_dict() for k in sorted(self.registry.keys())},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Exported", f"Saved to {path}")

    def generate_dispatch_class_stub(self):
        import ast

        filepath = os.path.join(os.path.dirname(__file__), "dispatch.py")
        if not os.path.isfile(filepath):
            messagebox.showerror("Error", "Could not find dispatch.py")
            return

        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()

        try:
            tree = ast.parse(source)
        except Exception as e:
            messagebox.showerror("Parse Error", f"Failed to parse dispatch.py: {e}")
            return

        method_lines = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Dispatch":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        first_line = item.lineno
                        if item.decorator_list:
                            first_line = item.decorator_list[0].lineno
                        method_lines[item.name] = first_line - 1
                break

        missing_impls = {}
        for cmd in self.registry.values():
            if cmd.implemented_by and cmd.implemented_by not in method_lines:
                missing_impls[cmd.implemented_by] = cmd

        if not missing_impls:
            messagebox.showinfo("Done", "No missing methods to stub!")
            return

        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        class_start = -1
        for i, line in enumerate(lines):
            if line.startswith("class Dispatch"):
                class_start = i
                break

        if class_start == -1:
            messagebox.showerror("Error", "Could not locate 'class Dispatch' in dispatch.py")
            return

        methods_in_file = sorted(method_lines.keys(), key=lambda x: x.lower())
        inserts_needed = sorted(missing_impls.keys(), key=lambda x: x.lower())

        insertion_points = {i: [] for i in range(len(lines) + 1)}

        for impl_name in inserts_needed:
            cmd = missing_impls[impl_name]

            insert_before_method = None
            for m in methods_in_file:
                if m.lower() > impl_name.lower():
                    insert_before_method = m
                    break

            if insert_before_method:
                insert_idx = method_lines[insert_before_method]
            else:
                insert_idx = len(lines)

            stub = "\n    @validate_params\n    @staticmethod\n"
            stub += f"    def {impl_name}("

            sig_args = []
            for i, p in enumerate(cmd.parameters):
                if p.optional:
                    sig_args.append(f"arg{i}=None")
                else:
                    sig_args.append(f"arg{i}")

            stub += ", ".join(sig_args)
            stub += "):\n        pass  # TODO\n"

            insertion_points[insert_idx].append(stub)

        new_source = []
        for i, line in enumerate(lines):
            if i in insertion_points:
                for stub in insertion_points[i]:
                    new_source.append(stub)
            new_source.append(line)

        if len(lines) in insertion_points:
            for stub in insertion_points[len(lines)]:
                new_source.append(stub)

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(new_source)

        messagebox.showinfo("Generated", f"Successfully injected {len(inserts_needed)} stubs into dispatch.py")


class StatusBar(tk.Frame):
    def __init__(self, master):
        tk.Frame.__init__(self, master)
        self.label = tk.Label(self)
        self.label.pack(side=tk.LEFT)
        self.pack(side=tk.BOTTOM, fill=tk.X)

    def set(self, newText):
        self.label.config(text=newText)
        timer = Timer(20, self.clear)
        timer.start()

    def clear(self):
        self.label.config(text="")


if __name__ == "__main__":
    root = tk.Tk()
    app = RegistryEditor(root)
    root.mainloop()
