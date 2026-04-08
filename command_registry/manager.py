import json
import os
import re
import ast
from datetime import datetime
from tkinter import messagebox, filedialog

try:
    from .models import Command, Parameter
except ImportError:
    from models import Command, Parameter

from typing import Dict


class RegistryManager:
    def __init__(self, app_root: str):
        self.app_root = app_root
        self.module_root = os.path.dirname(os.path.realpath(__file__))
        self.registry: Dict[str, Command] = {}
        self.file = os.path.join(self.module_root, "command_registry.json")
        try:
            with open(os.path.join(self.app_root, "command_registry_header.html"), "r", encoding="utf-8") as f:
                self.html_header = f.read()
        except FileNotFoundError:
            self.html_header = ""
        self.html_footer = "</body></html>"

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

    def regenerate_html_doc(self, name):
        docstring = self.registry[name].description
        docstring = self._link_commands(docstring)
        deprecated = self.registry[name].deprecated_by
        syntax = self.registry[name].syntax

        params = self.registry[name].parameters
        return self.get_html(name, docstring, deprecated, syntax, params)

    def import_json(self, path=None, show_message=True):
        if path is None:
            path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], title="Open Registry JSON")
        if not path:
            return False

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "commands" not in data:
            if show_message:
                messagebox.showerror("Error", "Invalid registry file: missing 'commands' key")
            return False

        self.registry.clear()
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

        if show_message:
            messagebox.showinfo("Imported", f"Loaded {len(self.registry)} entries from {path}")
        return True

    def export_json(self, file=None):
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

    def generate_dispatch(self):
        dropped_commands = []
        valid_registry = {}

        dispatch_file = os.path.join(self.app_root, "dispatch.py")
        stubbed_methods = set()
        if os.path.isfile(dispatch_file):
            with open(dispatch_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            current_method = None
            for line in lines:
                if line.strip().startswith("def "):
                    current_method = line.split("def ")[1].split("(")[0].strip()
                elif current_method and "pass" in line and "TODO" in line:
                    stubbed_methods.add(current_method)

        # Dynamic inspection of dispatch methods without pulling in GUI requirements of TAI
        dispatch_methods = set()
        if os.path.isfile(dispatch_file):
            with open(dispatch_file, "r", encoding="utf-8") as f:
                source = f.read()
            try:
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == "Dispatch":
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                dispatch_methods.add(item.name)
            except:
                pass

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
                if entry.implemented_by in dispatch_methods:
                    return True, ""
                else:
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
                if not entry.implemented_by:
                    dropped_commands.append((name, "No implementing_method or deprecated_by specified"))
                    continue

                if entry.implemented_by in stubbed_methods:
                    dropped_commands.append((name, f"Method {entry.implemented_by} is an unfinished stub"))
                    continue

                if entry.implemented_by not in dispatch_methods:
                    dropped_commands.append((name, f"Method {entry.implemented_by} not found in Dispatch"))
                    continue

            if not entry.description or len(entry.description.strip()) < 10:
                dropped_commands.append((name, "Docstring too short (minimum 10 characters)"))
                continue

            if not entry.test_path:
                dropped_commands.append((name, "No test path specified"))
                continue

            full_test_path = os.path.join(self.app_root, entry.test_path)
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

        dict_path = os.path.join(self.app_root, "dispatch_dict.py")
        with open(dict_path, "w", encoding="utf-8") as f:
            f.write("DISPATCH_DICT = {\n")
            for k, v in dispatch_dict.items():
                f.write(f"    '{k}': {v},\n")
            f.write("}\n")

        messagebox.showinfo("Generated", "Saved to dispatch_dict.py")

    def generate_docs(self, status_callback=None):
        if status_callback:
            status_callback("Building docs...")

        for k, v in self.registry.items():
            v.html_doc = self.regenerate_html_doc(k)

        docs_path = os.path.join(self.app_root, "docs.html")
        with open(docs_path, "w", encoding="utf-8") as f:
            f.write(self.html_header)
            for k in sorted(self.registry.keys()):
                f.write(f"{self.registry[k].html_doc}<br>")
                f.write("\n")
            f.write(self.html_footer)
        messagebox.showinfo("Generated", "Saved to docs.html")

    def generate_dispatch_class_stub(self):
        filepath = os.path.join(self.app_root, "dispatch.py")
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
