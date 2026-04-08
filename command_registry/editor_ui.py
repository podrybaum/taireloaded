import logging
import os
import pythoncom
import tkinter as tk
from tkinter import ttk, filedialog, Canvas, Scrollbar, messagebox
from threading import Timer
from tkwebview2.tkwebview2 import WebView2

try:
    from .models import Command, Parameter
    from .manager import RegistryManager
except ImportError:
    from models import Command, Parameter
    from manager import RegistryManager

pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
logging.getLogger("pywebview").setLevel(logging.CRITICAL + 1)


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


class RegistryEditor:
    def __init__(self, root, app_root: str):
        self.root = root
        self.app_root = app_root
        self.manager = RegistryManager(app_root)

        # References for UI convenience
        self.registry = self.manager.registry
        self.file = self.manager.file
        self.html_header = self.manager.html_header
        self.html_footer = self.manager.html_footer

        self.root.title("TAI Command Registry Editor")
        self.root.geometry("1324x768")
        self.param_rows = 0
        self.param_entries = []
        self.current_entry = None

        self._build_ui()
        self._refresh_listbox()
        self.name_entry.bind("<Tab>", self._copy_name_to_syntax, add="+")
        self.type_select_box.bind("<<ComboboxSelected>>", self._refresh_listbox, add="+")
        root.bind("<Return>", self._save_entry)
        root.bind("<Delete>", self._delete_command)
        self.status.set("Program initialized.")

        self._is_loading = False

        if os.path.isfile(self.file):
            self.manager.import_json(self.file, show_message=False)
            self._refresh_listbox()

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _populate_syntax_for_command_filter(self, event=None):
        if (
            self.category_dropdown.get() == "Command Filter"
            or (self.current_entry and self.current_entry.category == "Command Filter")
            or self.category_var.get() == "Command Filter"
        ):
            name = self.name_var.get().strip()
            self.syntax_var.set(f"{name} Skip this line unless")

    def _on_closing(self):
        if self.registry:
            self.manager.export_json(self.file)
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
        ttk.Button(bottom_frame, text="Export JSON", command=self.manager.export_json, takefocus=0).pack(
            side=tk.RIGHT, padx=5
        )
        ttk.Button(bottom_frame, text="Import JSON", command=self._import_json, takefocus=0).pack(side=tk.RIGHT, padx=5)
        ttk.Button(
            bottom_frame, text="Generate Dispatch Dict", command=self.manager.generate_dispatch, takefocus=0
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(
            bottom_frame,
            text="Generate HTML Docs",
            command=lambda: self.manager.generate_docs(status_callback=self.status.set),
            takefocus=0,
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(
            bottom_frame,
            text="Generate Dispatch class stub",
            command=self.manager.generate_dispatch_class_stub,
            takefocus=0,
        ).pack(side=tk.RIGHT, padx=5)

        self.editor_frame.columnconfigure(1, weight=1)
        self.editor_frame.columnconfigure(3, weight=1)
        self.editor_frame.rowconfigure(6, weight=1)
        self.editor_frame.rowconfigure(7, weight=0)

    def _delete_command(self, event=None):
        if event is not None and self.root.focus_get() != self.cmd_listbox:
            return
        if not self.current_entry or not getattr(self.current_entry, "name", None):
            return
        key = self.current_entry.name
        if messagebox.askyesno("Confirm", f"Delete {key}?"):
            if key in self.registry:
                del self.registry[key]
            self.current_entry = Command()
            self._update_ui_from_entry()
            self._refresh_listbox()

    def _import_json(self):
        if self.manager.import_json():
            self._refresh_listbox()

    def generate_html_doc(self, name):
        docstring = self.docstring_var.get().strip()
        docstring = self.manager._link_commands(docstring)
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

        return self.manager.get_html(name, docstring, deprecated, syntax, params)

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
        except Exception as e:
            print(f"Error in preview generation: {e}")

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
            initialdir=os.path.join(self.app_root, "tests", "commands"),
        )
        if not path:
            path = filedialog.askdirectory(
                title="Select Test Folder", initialdir=os.path.join(self.app_root, "tests", "commands")
            )
        if path:
            try:
                # Try to store a relative path to keep the registry portable
                rel_path = os.path.relpath(path, self.app_root)
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
            pos = row[6].get()
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
        self.current_entry.parameters = new_params
        self.current_entry.html_doc = self.generate_html_doc(name)

        key = name
        self.registry[key] = self.current_entry

        self._refresh_listbox()
        self._update_preview()
