"""Configuration module for Vitruvio.

Reads and writes a JSON configuration file. Factory defaults are baked in;
user overrides live in config.json. All configuration keys are in English
(backend). User-facing messages are localized via Traductor.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .localization import Traductor, traductor_mudo

#: Factory defaults (G-25: if it is JSON, nothing is hardcoded).
#: All keys in English.
FABRICA_VALUES: dict[str, Any] = {
    # -- Installation ---------------------------------------------------- #
    "installation_dir": ".",
    "delivery_dir": "entregas",
    "receipts_dir": ".vitruvio/receipts",
    "backups_dir": ".vitruvio/backups",
    "max_backups": 5,
    "max_backups_mb": 200,
    # -- Packages -------------------------------------------------------- #
    "max_packages": 20,
    "max_files": 8500,
    "max_size_mb": 1000,
    "max_compression_ratio": 0.95,
    # -- Interface ------------------------------------------------------- #
    "language": "es",
    "theme": "oscuro",
    "color": "no",
    # -- Behavior -------------------------------------------------------- #
    "self_test": False,
    "on_finish": "quarantine",
}

#: Available themes (3 mandatory from Muelle + 7 additional).
TEMAS_DISPONIBLES = (
    "oscuro", "claro", "sepia",
    "daltonico", "blanco_calido", "fosforo", "fosforo_color",
    "verde_apagado", "ambar", "alto_contraste",
)

#: Categories for `config view` (ordered like Muelle).
CATEGORIAS: dict[str, tuple[str, ...]] = {
    "Installation": (
        "installation_dir", "delivery_dir", "receipts_dir",
        "backups_dir", "max_backups", "max_backups_mb",
    ),
    "Packages": (
        "max_packages", "max_files", "max_size_mb", "max_compression_ratio",
    ),
    "Interface": (
        "language", "theme", "color",
    ),
    "Behavior": (
        "self_test", "on_finish",
    ),
}

#: Valid values for closed-vocabulary keys.
VALORES_VALIDOS: dict[str, tuple[str, ...]] = {
    "theme": TEMAS_DISPONIBLES,
    "color": ("sí", "si", "no", "yes", "true", "false", "1", "0"),
    "on_finish": ("quarantine", "clean", "none"),
    "language": ("es", "en"),
}


def _config_path() -> Path:
    """Return the path to the user's config.json.

    Vitruvio is portable: the config lives alongside the application, not in
    the user's home directory. Precedence:

    1. VITRUVIO_CONFIG environment variable
    2. ./config.json (current working directory)
    3. ./.vitruvio/config.json (application folder, portable)
    4. ~/.config/vitruvio/config.json (fallback only)
    """
    env = os.environ.get("VITRUVIO_CONFIG")
    if env:
        return Path(env)

    # 2. config.json in the current working directory.
    local = Path("config.json")
    if local.is_file():
        return local

    # 3. .vitruvio/config.json alongside the application (portable).
    app_local = Path(".vitruvio") / "config.json"
    if app_local.is_file():
        return app_local

    # 4. No config found: create one in the portable application folder.
    return Path(".vitruvio") / "config.json"


@dataclass
class Config:
    """Vitruvio configuration, backed by a JSON file on disk."""

    valores: dict[str, Any] = field(default_factory=lambda: dict(FABRICA_VALUES))
    path: Path = field(default_factory=_config_path)
    modificado: bool = field(default=False)

    @classmethod
    def cargar(cls) -> "Config":
        """Load configuration from disk, merging with factory defaults."""
        cfg = cls()
        if cfg.path.is_file():
            try:
                datos = json.loads(cfg.path.read_text(encoding="utf-8"))
                if isinstance(datos, dict):
                    cfg.valores = {**FABRICA_VALUES, **datos}
            except (json.JSONDecodeError, OSError):
                cfg.valores = dict(FABRICA_VALUES)
        else:
            cfg.valores = dict(FABRICA_VALUES)
        return cfg

    def guardar(self) -> None:
        """Persist current values to disk, creating portable folders if needed."""
        # Crear la carpeta portable .vitruvio si no existe.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Crear subcarpetas que Vitruvio necesita.
        for sub in ("receipts", "backups"):
            (self.path.parent / sub).mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.valores, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.modificado = False

    def obtener(self, clave: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.valores.get(clave, default)

    def poner(self, clave: str, valor: Any) -> None:
        """Set a configuration value and mark as modified."""
        self.valores[clave] = valor
        self.modificado = True

    def validar(self) -> list[str]:
        """Validate configuration values. Returns list of problems (empty = OK)."""
        problemas: list[str] = []

        # Integers.
        for clave in ("max_backups", "max_backups_mb", "max_packages",
                      "max_files", "max_size_mb"):
            try:
                int(self.obtener(clave, 0))
            except (TypeError, ValueError):
                problemas.append(f"{clave} must be an integer")

        # Compression ratio (0-1).
        ratio = self.obtener("max_compression_ratio", 0)
        try:
            r = float(ratio)
            if not (0.0 < r <= 1.0):
                problemas.append("max_compression_ratio must be between 0 and 1")
        except (TypeError, ValueError):
            problemas.append("max_compression_ratio must be a number")

        # Closed-vocabulary keys.
        for clave, permitidos in VALORES_VALIDOS.items():
            valor = str(self.obtener(clave, ""))
            if valor not in permitidos:
                opciones = ", ".join(permitidos)
                problemas.append(f"{clave} '{valor}' is invalid. Options: {opciones}")

        return problemas


def _origen_usuario(cfg: Config) -> set[str]:
    """Return keys that differ from factory defaults."""
    return {k for k, v in cfg.valores.items() if FABRICA_VALUES.get(k) != v}


def config_view(cfg: Config, tr: Traductor) -> str:
    """Render configuration grouped by categories."""
    lineas: list[str] = [tr.t("config.title", ruta=cfg.path)]
    lineas.append("")

    categorias_labels = {
        "Installation": tr.t("config.category_installation"),
        "Packages": tr.t("config.category_packages"),
        "Interface": tr.t("config.category_interface"),
        "Behavior": tr.t("config.category_behavior"),
    }

    for categoria, claves in CATEGORIAS.items():
        etiqueta = categorias_labels.get(categoria, f"┤ {categoria} ├")
        lineas.append(etiqueta)
        for clave in claves:
            if clave not in cfg.valores:
                continue
            valor = cfg.valores[clave]
            origen = "fabrica" if clave not in _origen_usuario(cfg) else "usuario"
            lineas.append(f"  {clave:26s} = {valor}  [{origen}]")
        lineas.append("")

    # Uncategorized keys.
    categorizadas = {k for claves in CATEGORIAS.values() for k in claves}
    extras = sorted(k for k in cfg.valores if k not in categorizadas)
    if extras:
        lineas.append(tr.t("config.category_others"))
        for clave in extras:
            valor = cfg.valores[clave]
            origen = "fabrica" if clave not in _origen_usuario(cfg) else "usuario"
            lineas.append(f"  {clave:26s} = {valor}  [{origen}]")
        lineas.append("")

    if cfg.modificado:
        lineas.append(tr.t("config.unsaved_changes"))

    return "\n".join(lineas)


def config_set(cfg: Config, clave: str, valor: str, tr: Traductor) -> str:
    """Set a configuration key to a parsed value."""
    parsed: Any = _parse_valor(valor)
    cfg.poner(clave, parsed)
    cfg.guardar()
    return tr.t("config.configured", clave_config=clave, valor=parsed, ruta=cfg.path)


def _parse_valor(valor: str) -> Any:
    """Parse a string value into int, float, bool, or str."""
    baja = valor.lower()
    if baja in ("true", "sí", "si", "yes", "1"):
        return True
    if baja in ("false", "no", "0"):
        return False
    try:
        return int(valor)
    except ValueError:
        pass
    try:
        return float(valor)
    except ValueError:
        pass
    return valor


def config_where(cfg: Config) -> str:
    """Return the config file path."""
    return str(cfg.path)


def config_validate(cfg: Config, tr: Traductor) -> str:
    """Validate configuration and return a report."""
    problemas = cfg.validar()
    if not problemas:
        return tr.t("config.valid")
    lineas = [tr.t("config.problems")]
    for p in problemas:
        lineas.append(tr.t("config.problem", problema=p))
    return "\n".join(lineas)


def config_help(tr: Traductor) -> str:
    """Return help text for the config command."""
    temas_str = ", ".join(TEMAS_DISPONIBLES)
    return f"""{tr.t("config.help_title")}

{tr.t("config.help_actions")}

{tr.t("config.available_keys")}

Installation:
  installation_dir   Default destination folder for installation
  delivery_dir       Delivery packages directory
  receipts_dir       Installation receipts directory
  backups_dir        Backup directory
  max_backups        Maximum number of backups
  max_backups_mb     Maximum backup size in MB

Packages:
  max_packages       Maximum packages tracked
  max_files          Maximum files per package
  max_size_mb        Maximum package size in MB
  max_compression_ratio  Acceptable compression ratio (0-1)

Interface:
  language           Interface language (es|en)
  theme              Visual theme: {temas_str}
  color              Use colors? (yes|no)

Behavior:
  self_test          Run self-test after installing
  on_finish          Action on finish (quarantine|clean|none)

{tr.t("config.examples_title")}
  vitruvio config set language en
  vitruvio config set theme fosforo
  vitruvio config set installation_dir /home/user/installations
  vitruvio config view
  vitruvio config where
"""


def manejar_config(args: list[str], cfg: Config, tr: Optional[Traductor] = None) -> int:
    """Dispatch the config subcommand. Returns POSIX exit code."""
    if tr is None:
        tr = traductor_mudo()

    if not args or args[0] in ("ayuda", "help", "--help", "-h"):
        print(config_help(tr))
        return 0

    accion = args[0].lower()

    if accion in ("ver", "view"):
        print(config_view(cfg, tr))
        return 0

    if accion in ("poner", "set"):
        if len(args) < 3:
            print("Uso: vitruvio config set <clave> <valor>")
            return 1
        clave = args[1]
        valor = args[2]
        print(config_set(cfg, clave, valor, tr))
        return 0

    if accion in ("validar", "validate"):
        print(config_validate(cfg, tr))
        return 0 if not cfg.validar() else 1

    if accion in ("donde", "where"):
        print(tr.t("config.where", ruta=config_where(cfg)))
        return 0

    print(f"Acción desconocida: {accion}")
    print(config_help(tr))
    return 1
