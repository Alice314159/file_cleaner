from dataclasses import dataclass


@dataclass
class ScanResult:
    path: str
    kind: str
    name: str
    size: int
    modified: float

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "kind": self.kind,
            "name": self.name,
            "size": self.size,
            "modified": self.modified,
        }
