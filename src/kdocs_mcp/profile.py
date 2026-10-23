"""Student profile: details that appear on every cover page, stored once on disk."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

DEFAULT_UNIVERSITY = "General Sir John Kotelawala Defence University"
DEFAULT_DEPARTMENT = "Department of Electrical Electronic and\nTelecommunication Engineering"
BUNDLED_LOGO = Path(__file__).parent / "assets" / "kdu_crest.png"


def config_dir() -> Path:
    env = os.environ.get("KDOCS_MCP_HOME") or os.environ.get("DOCUMENTING_MCP_HOME")
    if env:
        return Path(env)
    old = Path.home() / ".documenting-mcp"  # folder used before the rename
    new = Path.home() / ".kdocs-mcp"
    return old if old.is_dir() and not new.exists() else new


def default_output_dir() -> Path:
    docs = Path.home() / "Documents"
    return (docs if docs.is_dir() else Path.home()) / "KDocs"


@dataclass
class Profile:
    name: str = ""
    reg_no: str = ""
    intake: str = ""
    university: str = DEFAULT_UNIVERSITY
    department: str = DEFAULT_DEPARTMENT
    logo_path: str = ""
    output_dir: str = ""
    image_dir: str = ""  # the student's own image folder (default: Downloads/KDocs Images)

    def logo(self) -> Path:
        if self.logo_path and Path(self.logo_path).expanduser().is_file():
            return Path(self.logo_path).expanduser()
        return BUNDLED_LOGO

    def out_dir(self) -> Path:
        return Path(self.output_dir).expanduser() if self.output_dir else default_output_dir()

    def missing(self) -> list[str]:
        return [f for f in ("name", "reg_no", "intake") if not getattr(self, f)]


def _path() -> Path:
    return config_dir() / "profile.json"


def load_profile() -> Profile:
    p = _path()
    if not p.is_file():
        return Profile()
    data = json.loads(p.read_text(encoding="utf-8"))
    known = {f.name for f in fields(Profile)}
    return Profile(**{k: v for k, v in data.items() if k in known})


def save_profile(profile: Profile) -> Path:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")
    return p
