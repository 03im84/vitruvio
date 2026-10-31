"""Vitruvio command-line entry point.

Usage:
    python3 -m vitruvio install PACKAGE.zip --destiny <folder>
    python3 -m vitruvio verify --destiny <folder>
    python3 -m vitruvio undo --destiny <folder> --confirmation-from-file <file>
    python3 -m vitruvio history --destiny <folder>
    python3 -m vitruvio clean [MB] --destiny <folder>
    python3 -m vitruvio inspect PACKAGE.zip
    python3 -m vitruvio config [view|set|validate|where|help]
    python3 -m vitruvio --help | --version
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Añadir el directorio padre del paquete a sys.path para que la importación
# absoluta 'vitruvio.vitruvio' funcione sin depender de importación relativa.
# Esto es necesario porque 'py -m vitruvio' en Windows a veces no resuelve
# correctamente 'from .vitruvio import main'.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vitruvio.vitruvio import main
from vitruvio import __version__

SALUDO = f"""Vitruvio {__version__}
Universal installer with undo and verification.
Run 'python3 -m vitruvio --help' for usage.
"""


def cli_main(argv: Optional[list[str]] = None) -> int:
    return main(argv)


if __name__ == "__main__":
    raise SystemExit(cli_main(sys.argv[1:]))
