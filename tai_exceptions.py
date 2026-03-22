from bus import Bus


class SyntaxErr:
    def __init__(self, msg, line, pos, path):
        self.msg = msg
        self.line = line
        self.pos = pos
        self.path = path

    def throw(self):
        msg = f"SyntaxError: {self.msg} at line {self.line}, column {self.pos} in script file: {self.path}"
        Bus.emit("new_script_error", msg)
        Bus.emit("end_tease")


class RuntimeErr:
    def __init__(self, msg, line=None, pos=None, path=None):
        self.msg = msg
        self.line = line
        self.pos = pos
        self.path = path

    def throw(self):
        msg = f"RuntimeError: {self.msg} {'at line ' + self.line if self.line else ''}, {'column ' + self.pos if self.pos else ''} {'in script file: ' + self.path if self.path else ''}"
        Bus.emit("new_script_error", msg)
        Bus.emit("end_tease")


class ValueErr:
    def __init__(self, msg, line, pos, path):
        self.msg = msg
        self.line = line
        self.pos = pos
        self.path = path

    def throw(self):
        msg = f"ValueError: {self.msg} at line {self.line}, column {self.pos} in script file: {self.path}"
        Bus.emit("new_script_error", msg)
        Bus.emit("end_tease")


class NotImplementedErr:
    def __init__(self, msg, line, pos, path):
        self.msg = msg
        self.line = line
        self.pos = pos
        self.path = path

    def throw(self):
        msg = f"NotImplementedError: {self.msg} at line {self.line}, column {self.pos} in script file: {self.path}"
        Bus.emit("new_script_error", msg)
        Bus.emit("end_tease")


class TypeErr:
    def __init__(self, msg, line, pos, path):
        self.msg = msg
        self.line = line
        self.pos = pos
        self.path = path

    def throw(self):
        msg = f"TypeError: {self.msg} at line {self.line}, column {self.pos} in script file: {self.path}"
        Bus.emit("new_script_error", msg)
        Bus.emit("end_tease")
