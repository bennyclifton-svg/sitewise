"""Shared classification fixture corpus. See manifest.yaml."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml

MANIFEST = Path(__file__).parent / "manifest.yaml"


@dataclass(frozen=True, slots=True)
class Fixture:
    filename: str
    body: str
    expect: dict[str, str]
    note: str | None = None


def load_fixtures() -> list[Fixture]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return [
        Fixture(
            filename=item["filename"],
            body=item.get("body", ""),
            expect=item.get("expect", {}),
            note=item.get("note"),
        )
        for item in data["fixtures"]
    ]
