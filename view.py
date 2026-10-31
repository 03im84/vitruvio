"""Terminal UI for Vitruvio.

Boxes, panels, glifos and width measurement. Everything via terminal,
nothing graphical.
"""

from __future__ import annotations

import shutil
from typing import Optional

#: Fallback width when there is no terminal (no TTY).
ALWAYS_WIDTH = 66


def box_width(width: Optional[int] = None) -> int:
    """How wide a box should be.

    The window commands, the scale sets the ceiling. Without a TTY,
    shutil.get_terminal_size() returns a default and everything fits —
    that is why we measure with a real terminal when we can.
    """
    if width is not None:
        return width
    try:
        size = shutil.get_terminal_size(fallback=(ALWAYS_WIDTH, 20))
        return max(20, min(size.columns, ALWAYS_WIDTH))
    except Exception:
        return ALWAYS_WIDTH


GLIFOS = {
    "rama": "├─ ",
    "ultima": "└─ ",
    "linea": "─",
    "borde": "│",
    "esquina_sup_izq": "╭",
    "esquina_sup_der": "╮",
    "esquina_inf_izq": "╰",
    "esquina_inf_der": "╯",
}


def caja(titulo: str, lineas: list[str], ancho: int, paleta: dict, glifos: dict) -> list[str]:
    """Render a boxed panel.

    Returns the lines ready to print. `paleta` holds color keys
    (ok, error, aviso, titulo); `glifos` holds drawing characters.
    """
    resultado: list[str] = []
    borde_h = glifos["linea"] * (ancho - 2)
    resultado.append(f"{glifos['esquina_sup_izq']}{borde_h}{glifos['esquina_sup_der']}")
    titulo_line = f" {titulo} "
    padding = ancho - len(titulo_line) - 2
    if padding < 0:
        padding = 0
    resultado.append(f"{glifos['borde']} {titulo_line}{' ' * padding}{glifos['borde']}")
    resultado.append(f"{glifos['borde']}{' ' * (ancho - 2)}{glifos['borde']}")
    for linea in lineas:
        disponible = ancho - 4
        if len(linea) > disponible:
            linea = linea[:disponible - 3] + "..."
        resultado.append(f"{glifos['borde']}  {linea}{' ' * (ancho - 4 - len(linea))}{glifos['borde']}")
    resultado.append(f"{glifos['esquina_inf_izq']}{borde_h}{glifos['esquina_inf_der']}")
    return resultado
