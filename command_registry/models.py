from typing import List

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
