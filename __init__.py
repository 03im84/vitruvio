"""Vitruvio - Universal installer with undo and verification.

Reads a delivery package (ZIP + manifest + layout), installs it into a
destination folder, keeps a receipt of what it did, and can verify or undo
the installation leaving the tree exactly as it was.

No project-specific knowledge: it only knows about contracts, receipts and
plans. Safe to reuse for any project.
"""

__version__ = "1.0.0-r13"

__all__ = ["Vitruvio", "version"]


def version() -> str:
    return __version__
