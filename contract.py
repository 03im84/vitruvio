"""Contract module.

Defines the data model Vitruvio understands: manifests, receipts, plans,
files, actions and untouchable paths. Project-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

#: Closed vocabulary of actions a file can have in a plan.
ACTION_ADD = "add"
ACTION_REPLACE = "replace"
ACTION_SAME = "same"
ACTION_REMOVE = "remove"

#: Closed vocabulary of receipt states.
STATE_INSTALLING = "installing"
STATE_TESTING = "testing"
STATE_INSTALLED = "installed"
STATE_UNDOING = "undoing"
STATE_UNDONE = "undone"
STATE_INCOMPLETE = "incomplete"

#: Schema versions.
SCHEMA_MANIFEST = "manifest.v1"
SCHEMA_RECEIPT = "receipt.v1"


@dataclass
class File:
    """A single file in a manifest, receipt or plan."""

    path: str
    fingerprint: str          # sha256 of file contents
    action: str               # one of ACTION_*
    previous_fingerprint: Optional[str] = None
    size: int = 0


@dataclass
class Manifest:
    """What a delivery package declares it contains."""

    schema: str
    delivery: str
    version: str
    date: str
    files: tuple[File, ...]


@dataclass
class Receipt:
    """What Vitruvio actually installed in a destination."""

    schema: str
    state: str
    delivery: str
    version: str
    version_previous: Optional[str] = None
    package_fingerprint: str = ""
    manifest_fingerprint: str = ""
    package_path: str = ""
    installed_in: str = ""
    date: str = ""
    backups: str = ""
    backup_bytes: int = 0
    files: tuple[File, ...] = field(default_factory=tuple)


@dataclass
class Plan:
    """What an installation will do: add, replace, keep, remove."""

    add: tuple[File, ...]
    replace: tuple[File, ...]
    same: tuple[File, ...]
    remove: tuple[File, ...] = ()
    copy_bytes: int = 0
    needed_bytes: int = 0

    @property
    def touches(self) -> tuple[File, ...]:
        """Files that will be written or checked."""
        return self.add + self.replace + self.same

    @property
    def has_work(self) -> bool:
        """True if there is anything to do at all."""
        return bool(self.add or self.replace or self.same or self.remove)


#: Paths that are never removed, even if an old receipt names them.
#: Person's data: config, users, records.
UNTOUCHABLE_FILES = frozenset({
    "config.json",
    "usuarios.json",
    "users.json",
    "accounts.json",
})

UNTOUCHABLE_FOLDERS = frozenset({
    "users",
    "registros",
    "records",
    "accounts",
    ".muelle",
    ".vitruvio",
})


def is_untouchable(path: str) -> bool:
    """True if `path` is person's data and must never be removed.

    Belt and suspenders: an old receipt should never name these, but if it
    ever does, this stops deletion before anything is touched.
    """
    clean = str(path).replace("\\", "/").strip("/")
    first = clean.split("/")[0]
    return clean in UNTOUCHABLE_FILES or first in UNTOUCHABLE_FOLDERS
