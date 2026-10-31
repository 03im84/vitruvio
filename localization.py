"""Localización (i18n) para Vitruvio.

Regla: ninguna cadena visible para la persona vive en el código.
Todo texto se pide por clave a un `Traductor`, que lo busca en
`resources/i18n/<idioma>.json`. Añadir un idioma = añadir un fichero JSON.

Formato del catálogo: un único objeto JSON plano con claves separadas por puntos.
    { "app.nombre": "Vitruvio", "error.paquete_no_encontrado": "Paquete no encontrado: {ruta}" }
"""

from __future__ import annotations

import json
from pathlib import Path

IDIOMA_BASE = "es"
MENSAJE_ULTIMO_RECURSO = (
    "No se pudo iniciar. Revisa el archivo de ajustes o los permisos de la carpeta.\n"
    "Could not start. Check the settings file or the folder permissions.\n"
)
IDIOMAS_MINIMOS = ("es", "en")
_CARPETA = Path(__file__).resolve().parent / "resources" / "i18n"


class _Parametros(dict):
    """Diccionario tolerante: si falta un parámetro no revienta el mensaje."""

    def __missing__(self, clave: str) -> str:  # pragma: no cover - defensa
        return "?"


class Traductor:
    """Traduce claves a texto en el idioma activo, con reserva al idioma base."""

    def __init__(self, idioma: str, catalogos: dict[str, dict[str, str]]):
        self._catalogos = catalogos
        self._idioma = idioma if idioma in catalogos else IDIOMA_BASE

    @classmethod
    def cargar(cls, idioma: str = IDIOMA_BASE, carpeta: Path | None = None) -> "Traductor":
        carpeta = carpeta or _CARPETA
        catalogos: dict[str, dict[str, str]] = {}
        for fichero in sorted(carpeta.glob("*.json")):
            try:
                datos = json.loads(fichero.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(datos, dict):
                catalogos[fichero.stem] = {k: str(v) for k, v in datos.items()}
        if IDIOMA_BASE not in catalogos:
            catalogos[IDIOMA_BASE] = {}
        return cls(idioma, catalogos)

    @property
    def idioma(self) -> str:
        return self._idioma

    @property
    def idiomas(self) -> tuple[str, ...]:
        return tuple(sorted(self._catalogos))

    def cambiar(self, idioma: str) -> bool:
        if idioma in self._catalogos:
            self._idioma = idioma
            return True
        return False

    def plural(self, base: str, cantidad: int, **datos) -> str:
        """Elige entre la forma de uno y la de muchos."""
        clave = "%s.uno" % base if abs(int(cantidad)) == 1 else "%s.varios" % base
        return self.t(clave, cantidad=cantidad, **datos)

    def tiene(self, clave: str) -> bool:
        return clave in self._catalogos.get(self._idioma, {}) or clave in self._catalogos[IDIOMA_BASE]

    def t(self, clave: str, **parametros) -> str:
        """Devuelve el texto de `clave`. Nunca lanza excepción."""
        plantilla = self._catalogos.get(self._idioma, {}).get(clave)
        if plantilla is None:
            plantilla = self._catalogos[IDIOMA_BASE].get(clave)
        if plantilla is None:
            return "<%s>" % clave
        if not parametros:
            return plantilla
        try:
            return plantilla.format_map(_Parametros(parametros))
        except (IndexError, ValueError):
            return plantilla

    def claves(self, idioma: str | None = None) -> set[str]:
        return set(self._catalogos.get(idioma or self._idioma, {}))


def traductor_mudo() -> Traductor:
    """Traductor vacío, útil en arranques tempranos y en pruebas unitarias."""
    return Traductor(IDIOMA_BASE, {IDIOMA_BASE: {}})
