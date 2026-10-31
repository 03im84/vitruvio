"""Vitruvio installer.

Universal installer with undo and verification. Reads a delivery package
(ZIP + manifest + layout), installs it into a destination folder, keeps a
receipt of what it did, and can verify or undo.

Grammar of actions (commands and flags are always in English):
    vitruvio install PACKAGE.zip --destiny <folder>
    vitruvio verify --destiny <folder>
    vitruvio undo --destiny <folder> --confirmation-from-file <file>
    vitruvio history --destiny <folder>
    vitruvio clean [MB] --destiny <folder>
    vitruvio inspect PACKAGE.zip
    vitruvio config [view|set|validate|where|help]
    vitruvio --help | --version

User-facing messages are localized according to the selected language (es|en).
Configuration keys are always in English.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from . import contract
from .config import (
    CATEGORIAS,
    FABRICA_VALUES,
    Config,
    manejar_config,
    TEMAS_DISPONIBLES,
)
from .layout import fingerprint_of, safe_path, list_python_files
from .localization import Traductor, traductor_mudo

SALIDA_BIEN, SALIDA_USO, SALIDA_ERROR = 0, 1, 2

#: Grammar of top-level verbs (always in English).
ACCIONES = {
    "install": "install",
    "verify": "verify",
    "undo": "undo",
    "history": "history",
    "clean": "clean",
    "inspect": "inspect",
    "config": "config",
}

#: Synonyms accepted for commands (English canonical; Spanish aliases map to them).
SINONIMOS = {
    "instala": "install",
    "instalar": "install",
    "borrar": "undo",
    "deshacer": "undo",
    "comprobar": "verify",
    "verificar": "verify",
    "limpia": "clean",
    "limpiar": "clean",
}

ARCHIVO_MANIFIESTO = "manifiesto.json"


@dataclass
class Contexto:
    """Execution context for a Vitruvio command."""

    accion: str
    paquete: Optional[Path]
    destino: Path
    salida: object
    opciones: dict = field(default_factory=dict)
    recibos: Path = field(default_factory=Path)
    pantalla: object = field(default_factory=object)
    textos: object = field(default_factory=object)
    anota: callable = field(default_factory=lambda *_: None)


# ---------------------------------------------------------------------------
# Localización
# ---------------------------------------------------------------------------

def _tr(cfg: Optional[Config] = None) -> Traductor:
    """Create a Translator with the language from configuration."""
    if cfg is None:
        return traductor_mudo()
    idioma = cfg.obtener("language", "es")
    return Traductor.cargar(idioma)


# ---------------------------------------------------------------------------
# Manifest / receipt helpers
# ---------------------------------------------------------------------------

def leer_manifiesto(zip_abierto: zipfile.ZipFile) -> contract.Manifest:
    """Read and validate the manifest from an open ZIP."""
    datos = zip_abierto.read(ARCHIVO_MANIFIESTO)
    crudo = json.loads(datos.decode("utf-8"))
    archivos = tuple(
        contract.File(
            path=a["ruta"],
            fingerprint=a["firma"],
            action=a["accion"],
            size=a.get("bytes", 0),
        )
        for a in crudo.get("archivos", [])
    )
    return contract.Manifest(
        schema=crudo.get("esquema", contract.SCHEMA_MANIFEST),
        delivery=crudo.get("entrega", "undeclared"),
        version=crudo.get("version", "0.0.0"),
        date=crudo.get("fecha", "1970-01-01"),
        files=archivos,
    )


def recibo_ultimo(recibos_dir: Path) -> Optional[contract.Receipt]:
    """Return the most recent receipt, or None."""
    if not recibos_dir.is_dir():
        return None
    recibos = sorted(recibos_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    for r in recibos:
        try:
            datos = json.loads(r.read_text(encoding="utf-8"))
            archivos = tuple(
                contract.File(
                    path=f["ruta"],
                    fingerprint=f["firma"],
                    action=f["accion"],
                    previous_fingerprint=f.get("firma_anterior"),
                    size=f.get("bytes", 0),
                )
                for f in datos.get("archivos", [])
            )
            return contract.Receipt(
                schema=datos.get("esquema", contract.SCHEMA_RECEIPT),
                state=datos.get("estado", contract.STATE_INCOMPLETE),
                delivery=datos.get("entrega", ""),
                version=datos.get("version", ""),
                version_previous=datos.get("version_anterior"),
                package_fingerprint=datos.get("package_fingerprint", ""),
                manifest_fingerprint=datos.get("manifest_fingerprint", ""),
                package_path=datos.get("package_path", ""),
                installed_in=datos.get("installed_in", ""),
                date=datos.get("fecha", ""),
                backups=datos.get("backups", ""),
                backup_bytes=datos.get("backup_bytes", 0),
                files=archivos,
            )
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

def plan_de_instalacion(manifiesto: contract.Manifest, destino: Path,
                        anterior: Optional[contract.Receipt] = None) -> contract.Plan:
    """What to add, replace, keep and remove. Only reads."""
    anadir: list[contract.File] = []
    reemplazar: list[contract.File] = []
    iguales: list[contract.File] = []
    bytes_copia = 0

    for archivo in manifiesto.files:
        actual = destino / archivo.path
        if not actual.exists():
            anadir.append(
                contract.File(
                    path=archivo.path,
                    fingerprint=archivo.fingerprint,
                    action=contract.ACTION_ADD,
                    previous_fingerprint=None,
                    size=archivo.size,
                )
            )
            continue
        firma_actual = fingerprint_of(actual)
        if firma_actual == archivo.fingerprint:
            iguales.append(
                contract.File(
                    path=archivo.path,
                    fingerprint=archivo.fingerprint,
                    action=contract.ACTION_SAME,
                    previous_fingerprint=firma_actual,
                    size=archivo.size,
                )
            )
            continue
        reemplazar.append(
            contract.File(
                path=archivo.path,
                fingerprint=archivo.fingerprint,
                action=contract.ACTION_REPLACE,
                previous_fingerprint=firma_actual,
                size=archivo.size,
            )
        )
        bytes_copia += actual.stat().st_size

    retirar: list[contract.File] = []
    nuevos = {a.path for a in manifiesto.files}
    for viejo in getattr(anterior, "files", ()) or ():
        if viejo.path in nuevos or viejo.action in (contract.ACTION_SAME, contract.ACTION_REMOVE):
            continue
        if contract.is_untouchable(viejo.path):
            continue
        actual = destino / viejo.path
        if not actual.is_file():
            continue
        retirar.append(
            contract.File(
                path=viejo.path,
                fingerprint=fingerprint_of(actual),
                action=contract.ACTION_REMOVE,
                previous_fingerprint=viejo.fingerprint,
                size=actual.stat().st_size,
            )
        )
        bytes_copia += actual.stat().st_size

    bytes_nuevos = sum(a.size for a in anadir) + sum(a.size for a in reemplazar)
    return contract.Plan(
        add=tuple(anadir),
        replace=tuple(reemplazar),
        same=tuple(iguales),
        remove=tuple(retirar),
        copy_bytes=bytes_copia,
        needed_bytes=bytes_nuevos + bytes_copia,
    )


# ---------------------------------------------------------------------------
# Install execution helpers
# ---------------------------------------------------------------------------

def _copia_de_seguridad(destino: Path, plan: contract.Plan,
                        copias_dir: Path) -> tuple[str, int]:
    """Back up files that will be replaced or removed."""
    copias_dir.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    carpeta_backup = copias_dir / marca
    carpeta_backup.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    for archivo in plan.replace + plan.remove:
        origen = destino / archivo.path
        if not origen.is_file():
            continue
        destino_bk = carpeta_backup / archivo.path
        destino_bk.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen, destino_bk)
        total_bytes += origen.stat().st_size

    return marca, total_bytes


def _escribir_archivos(destino: Path, plan: contract.Plan,
                       zip_abierto: zipfile.ZipFile) -> None:
    """Write new and replaced files from the package ZIP into destination."""
    for archivo in plan.add + plan.replace:
        origen_zip = archivo.path
        try:
            datos = zip_abierto.read(origen_zip)
        except KeyError:
            raise FileNotFoundError(
                f"Archivo '{origen_zip}' no encontrado en el paquete ZIP"
            )
        actual = safe_path(destino, archivo.path)
        actual.parent.mkdir(parents=True, exist_ok=True)
        actual.write_bytes(datos)


def _retirar_archivos(destino: Path, plan: contract.Plan) -> None:
    """Remove files marked for removal from the destination."""
    for archivo in plan.remove:
        actual = destino / archivo.path
        if actual.is_file() and not contract.is_untouchable(archivo.path):
            actual.unlink()


def _rollback_instalacion(destino: Path, plan: contract.Plan,
                          copias_dir: Path, marca_bk: str) -> None:
    """Rollback automático: restaura el estado anterior desde el backup."""
    carpeta_backup = copias_dir / marca_bk
    if not carpeta_backup.is_dir():
        return

    # Restaurar archivos que se fueron a reemplazar o eliminar
    for archivo in plan.replace + plan.remove:
        origen_bk = carpeta_backup / archivo.path
        actual = destino / archivo.path
        if origen_bk.is_file():
            actual.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origen_bk, actual)
        elif actual.is_file():
            # El archivo se eliminó y no hay backup, eliminarlo del destino
            actual.unlink()

    # Eliminar archivos nuevos que se agregaron (no existían antes)
    for archivo in plan.add:
        actual = destino / archivo.path
        if actual.is_file():
            actual.unlink()
            # Eliminar directorios vacíos que quedaron
            padre = actual.parent
            while padre != destino:
                try:
                    padre.rmdir()
                except OSError:
                    break
                padre = padre.parent


def _verificar_arbol(destino: Path, manifiesto: contract.Manifest) -> list[str]:
    """Verify installed files match the manifest fingerprints.

    The manifest.json itself is not verified: it is the control file and its
    fingerprint cannot match what it declares (it is written after calculating
    the others).
    """
    problemas: list[str] = []
    for archivo in manifiesto.files:
        if archivo.path.endswith("manifiesto.json"):
            continue
        actual = destino / archivo.path
        if not actual.is_file():
            problemas.append(f"Falta: {archivo.path}")
            continue
        firma = fingerprint_of(actual)
        if firma != archivo.fingerprint:
            problemas.append(
                f"Huella distinta: {archivo.path} "
                f"(esperado {archivo.fingerprint[:12]}..., obtenido {firma[:12]}...)"
            )
    return problemas


def recibir_guardar(recibo: contract.Receipt, recibos_dir: Path) -> None:
    """Persist a receipt as JSON in the receipts folder."""
    recibos_dir.mkdir(parents=True, exist_ok=True)
    fecha_segura = recibo.date.replace(":", "-").replace("T", "_")
    nombre = f"{fecha_segura}-{recibo.delivery}.json"
    datos = {
        "esquema": recibo.schema,
        "estado": recibo.state,
        "entrega": recibo.delivery,
        "version": recibo.version,
        "version_anterior": recibo.version_previous,
        "package_fingerprint": recibo.package_fingerprint,
        "manifest_fingerprint": recibo.manifest_fingerprint,
        "package_path": recibo.package_path,
        "installed_in": recibo.installed_in,
        "fecha": recibo.date,
        "backups": recibo.backups,
        "backup_bytes": recibo.backup_bytes,
        "archivos": [
            {
                "ruta": f.path,
                "firma": f.fingerprint,
                "accion": f.action,
                "firma_anterior": f.previous_fingerprint,
                "bytes": f.size,
            }
            for f in recibo.files
        ],
    }
    (recibos_dir / nombre).write_text(
        json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Command implementations (messages localized via Traductor)
# ---------------------------------------------------------------------------

def _instalar_paquete(paquete_zip: Path, destino: Path, cfg: Config) -> int:
    """Full install flow: read manifest, plan, backup, write, receipt, verify."""
    tr = _tr(cfg)
    recibos_dir = destino / cfg.obtener("receipts_dir", ".vitruvio/receipts")
    copias_dir = destino / cfg.obtener("backups_dir", ".vitruvio/backups")

    # 1. Open package and read manifest.
    try:
        zf = zipfile.ZipFile(paquete_zip)
    except (zipfile.BadZipFile, OSError) as exc:
        print(tr.t("error.package_invalid", exc=exc))
        return SALIDA_ERROR

    with zf:
        try:
            manifiesto = leer_manifiesto(zf)
        except (KeyError, json.JSONDecodeError) as exc:
            print(tr.t("error.manifest_invalid", exc=exc))
            return SALIDA_ERROR

    # 2. Plan against destination and previous receipt.
    anterior = recibo_ultimo(recibos_dir)
    plan = plan_de_instalacion(manifiesto, destino, anterior)

    if not plan.has_work:
        print(tr.t("message.no_changes"))
        return SALIDA_BIEN

    # Show plan summary.
    print(tr.t("message.package", delivery=manifiesto.delivery, version=manifiesto.version))
    print(tr.t("message.add", cuenta=len(plan.add)))
    print(tr.t("message.replace", cuenta=len(plan.replace)))
    print(tr.t("message.keep", cuenta=len(plan.same)))
    print(tr.t("message.remove", cuenta=len(plan.remove)))

    # 3. Backup files to be replaced/removed.
    marca_bk, bytes_bk = _copia_de_seguridad(destino, plan, copias_dir)

    try:
        # 4. Write new/replaced files from ZIP.
        with zipfile.ZipFile(paquete_zip) as zf:
            _escribir_archivos(destino, plan, zf)

        # 5. Remove files marked for removal.
        _retirar_archivos(destino, plan)

        # 6. Save receipt.
        ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        paquete_firma = fingerprint_of(paquete_zip)
        with zipfile.ZipFile(paquete_zip) as zf:
            manifiesto_bytes = zf.read(ARCHIVO_MANIFIESTO)
        manifiesto_firma = hashlib.sha256(manifiesto_bytes).hexdigest()

        recibo = contract.Receipt(
            schema=contract.SCHEMA_RECEIPT,
            state=contract.STATE_INSTALLED,
            delivery=manifiesto.delivery,
            version=manifiesto.version,
            version_previous=anterior.version if anterior else None,
            package_fingerprint=paquete_firma,
            manifest_fingerprint=manifiesto_firma,
            package_path=str(paquete_zip),
            installed_in=str(destino),
            date=ahora,
            backups=marca_bk,
            backup_bytes=bytes_bk,
            files=tuple(
                contract.File(
                    path=f.path,
                    fingerprint=f.fingerprint,
                    action=f.action,
                    previous_fingerprint=f.previous_fingerprint,
                    size=f.size,
                )
                for f in plan.add + plan.replace + plan.same
            ),
        )
        recibir_guardar(recibo, recibos_dir)

        # 7. Verify.
        problemas = _verificar_arbol(destino, manifiesto)
        if problemas:
            print(tr.t("message.install_warnings"))
            for p in problemas:
                print(tr.t("message.problem", problema=p))
            raise RuntimeError("Verificación falló: archivos no coinciden con el manifiesto")

    except Exception as exc:
        # Rollback automático: restaurar desde el backup
        print(tr.t("error.install_failed", exc=exc))
        print(tr.t("message.rollback_starting"))
        _rollback_instalacion(destino, plan, copias_dir, marca_bk)
        print(tr.t("message.rollback_completed"))
        return SALIDA_ERROR

    print(tr.t("message.installed", delivery=manifiesto.delivery,
               version=manifiesto.version, destino=destino))
    print(tr.t("message.backup", marca=marca_bk, bytes=bytes_bk))

    # 8. Post-install action (on_finish).
    on_finish = cfg.obtener("on_finish", "none")
    if on_finish == "clean":
        try:
            paquete_zip.unlink()
            print(tr.t("message.package_cleaned"))
        except OSError:
            pass
    elif on_finish == "quarantine":
        cuarentena_dir = destino / ".vitruvio" / "quarantine"
        cuarentena_dir.mkdir(parents=True, exist_ok=True)
        destino_cuarentena = cuarentena_dir / paquete_zip.name
        shutil.move(str(paquete_zip), str(destino_cuarentena))
        print(tr.t("message.package_quarantined", ruta=destino_cuarentena))

    return SALIDA_BIEN


def _cmd_install(argv: list[str], cfg: Config) -> int:
    """vitruvio install [PACKAGE.zip] [--destiny <folder>]"""
    tr = _tr(cfg)
    parser = argparse.ArgumentParser(prog="vitruvio install", add_help=False)
    parser.add_argument("paquete", nargs="?", help="Ruta al archivo .zip del paquete")
    parser.add_argument(
        "--destiny", default=cfg.obtener("installation_dir", "."),
        help="Carpeta de destino (por defecto: installation_dir del config)",
    )
    args, _ = parser.parse_known_args(argv)

    paquete_path = Path(args.paquete) if args.paquete else None
    if paquete_path is None:
        delivery_dir = Path(cfg.obtener("delivery_dir", "entregas"))
        if not delivery_dir.is_dir():
            print(tr.t("error.no_delivery_dir", ruta=delivery_dir))
            return SALIDA_ERROR
        zips = sorted(delivery_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not zips:
            print(tr.t("error.no_package_in_delivery", ruta=delivery_dir))
            return SALIDA_ERROR
        paquete_path = zips[0]
        print(tr.t("message.using_package", ruta=paquete_path))

    if not paquete_path.is_file():
        print(tr.t("error.package_not_found", ruta=paquete_path))
        return SALIDA_ERROR

    destino = Path(args.destiny)
    destino.mkdir(parents=True, exist_ok=True)

    return _instalar_paquete(paquete_path, destino, cfg)


def _cmd_verify(argv: list[str], cfg: Config) -> int:
    """vitruvio verify --destiny <folder>"""
    tr = _tr(cfg)
    parser = argparse.ArgumentParser(prog="vitruvio verify", add_help=False)
    parser.add_argument("--destiny", required=True, help="Carpeta de destino")
    args, _ = parser.parse_known_args(argv)

    destino = Path(args.destiny)
    recibos_dir = destino / cfg.obtener("receipts_dir", ".vitruvio/receipts")
    anterior = recibo_ultimo(recibos_dir)

    if anterior is None:
        print(tr.t("error.no_receipt", accion="verificar"))
        return SALIDA_USO

    print(tr.t("message.verifying", delivery=anterior.delivery,
               version=anterior.version, destino=destino))
    problemas = _verificar_arbol(destino, anterior)

    if problemas:
        print(tr.t("message.problems_found", cuenta=len(problemas)))
        for p in problemas:
            print(tr.t("message.problem", problema=p))
        return SALIDA_ERROR

    print(tr.t("message.verified"))
    return SALIDA_BIEN


def _cmd_undo(argv: list[str], cfg: Config) -> int:
    """vitruvio undo --destiny <folder> --confirmation-from-file <file>"""
    tr = _tr(cfg)
    parser = argparse.ArgumentParser(prog="vitruvio undo", add_help=False)
    parser.add_argument("--destiny", required=True, help="Carpeta de destino")
    parser.add_argument("--confirmation-from-file", required=True,
                        help="Archivo que contiene la palabra de confirmación")
    args, _ = parser.parse_known_args(argv)

    destino = Path(args.destiny)
    recibos_dir = destino / cfg.obtener("receipts_dir", ".vitruvio/receipts")
    copias_dir = destino / cfg.obtener("backups_dir", ".vitruvio/backups")

    anterior = recibo_ultimo(recibos_dir)
    if anterior is None:
        print(tr.t("error.no_receipt", accion="deshacer"))
        return SALIDA_USO

    # Read confirmation file.
    try:
        confirmacion = Path(args.confirmation_from_file).read_text(encoding="utf-8").strip()
    except OSError as exc:
        print(tr.t("error.confirmation_file_unreadable", exc=exc))
        return SALIDA_ERROR

    # The confirmation must contain the delivery name.
    if anterior.delivery not in confirmacion:
        print(tr.t("error.invalid_confirmation"))
        return SALIDA_ERROR

    # Restore from backup.
    backup_dir = copias_dir / anterior.backups
    if not backup_dir.is_dir():
        print(tr.t("error.backup_not_found", ruta=backup_dir))
        return SALIDA_ERROR

    restaurados = 0
    for f in anterior.files:
        bk = backup_dir / f.path
        actual = destino / f.path
        if f.action == contract.ACTION_REMOVE:
            if bk.is_file():
                actual.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(bk, actual)
                restaurados += 1
        elif f.action in (contract.ACTION_ADD, contract.ACTION_REPLACE):
            if actual.is_file():
                actual.unlink()
                restaurados += 1
            if bk.is_file():
                actual.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(bk, actual)
                restaurados += 1

    # Mark receipt as undone.
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    recibo_deshecho = contract.Receipt(
        schema=contract.SCHEMA_RECEIPT,
        state=contract.STATE_UNDONE,
        delivery=anterior.delivery,
        version=anterior.version,
        version_previous=anterior.version_previous,
        package_fingerprint=anterior.package_fingerprint,
        manifest_fingerprint=anterior.manifest_fingerprint,
        package_path=anterior.package_path,
        installed_in=anterior.installed_in,
        date=ahora,
        backups=anterior.backups,
        backup_bytes=anterior.backup_bytes,
        files=anterior.files,
    )
    recibir_guardar(recibo_deshecho, recibos_dir)

    print(tr.t("message.undone", delivery=anterior.delivery,
               version=anterior.version))
    print(tr.t("message.restored", cuenta=restaurados))
    return SALIDA_BIEN


def _cmd_history(argv: list[str], cfg: Config) -> int:
    """vitruvio history --destiny <folder>"""
    tr = _tr(cfg)
    parser = argparse.ArgumentParser(prog="vitruvio history", add_help=False)
    parser.add_argument("--destiny", required=True, help="Carpeta de destino")
    args, _ = parser.parse_known_args(argv)

    destino = Path(args.destiny)
    recibos_dir = destino / cfg.obtener("receipts_dir", ".vitruvio/receipts")
    if not recibos_dir.is_dir():
        print(tr.t("message.no_history", destino=destino))
        return SALIDA_BIEN

    recibos = sorted(recibos_dir.iterdir(), key=lambda p: p.stat().st_mtime)
    print(tr.t("message.history_title", destino=destino))
    for r in recibos:
        try:
            datos = json.loads(r.read_text(encoding="utf-8"))
            print(tr.t("message.history_entry",
                       fecha=datos.get('fecha', ''),
                       delivery=datos.get('delivery', ''),
                       version=datos.get('version', ''),
                       estado=datos.get('estado', '')))
        except Exception:
            print(tr.t("message.receipt_unreadable", nombre=r.name))
    return SALIDA_BIEN


def _cmd_clean(argv: list[str], cfg: Config) -> int:
    """vitruvio clean [MB] --destiny <folder>"""
    tr = _tr(cfg)
    parser = argparse.ArgumentParser(prog="vitruvio clean", add_help=False)
    parser.add_argument("mb", nargs="?", type=int, default=None,
                        help="Tamaño máximo de copias a conservar en MB")
    parser.add_argument("--destiny", required=True, help="Carpeta de destino")
    args, _ = parser.parse_known_args(argv)

    destino = Path(args.destiny)

    # --- Limpieza de backups (por tamaño) ---
    copias_dir = destino / cfg.obtener("backups_dir", ".vitruvio/backups")
    borrados_backups = 0
    if copias_dir.is_dir():
        limite_mb = args.mb if args.mb is not None else cfg.obtener("max_backups_mb", 200)
        limite_bytes = limite_mb * 1024 * 1024

        copias = sorted(copias_dir.iterdir(), key=lambda p: p.stat().st_mtime)
        total = sum(p.stat().st_size for p in copias if p.is_file())
        for copia in copias:
            if total <= limite_bytes:
                break
            if copia.is_dir():
                tam = sum(f.stat().st_size for f in copia.rglob("*") if f.is_file())
                shutil.rmtree(copia)
                total -= tam
                borrados_backups += 1

    # --- Limpieza de recibos (por cantidad, mantiene los más recientes) ---
    recibos_dir = destino / cfg.obtener("receipts_dir", ".vitruvio/receipts")
    borrados_recibos = 0
    if recibos_dir.is_dir():
        max_recibos = cfg.obtener("max_packages", 20)
        recibos = sorted(recibos_dir.iterdir(), key=lambda p: p.stat().st_mtime,
                         reverse=True)
        for recibo in recibos[max_recibos:]:
            recibo.unlink()
            borrados_recibos += 1

    print(tr.t("message.cleaned", cuenta=borrados_backups))
    if borrados_recibos > 0:
        print(tr.t("message.receipts_cleaned", cuenta=borrados_recibos))
    return SALIDA_BIEN


def _cmd_inspect(argv: list[str], cfg: Config) -> int:
    """vitruvio inspect PACKAGE.zip"""
    tr = _tr(cfg)
    parser = argparse.ArgumentParser(prog="vitruvio inspect", add_help=False)
    parser.add_argument("paquete", help="Ruta al archivo .zip del paquete")
    args, _ = parser.parse_known_args(argv)

    paquete = Path(args.paquete)
    if not paquete.is_file():
        print(tr.t("error.package_not_found", ruta=paquete))
        return SALIDA_ERROR

    try:
        with zipfile.ZipFile(paquete) as zf:
            manifiesto = leer_manifiesto(zf)
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
        print(tr.t("error.package_invalid", exc=exc))
        return SALIDA_ERROR

    print(tr.t("message.package_title", delivery=manifiesto.delivery,
               version=manifiesto.version))
    print(tr.t("message.schema", schema=manifiesto.schema))
    print(tr.t("message.date", fecha=manifiesto.date))
    print(tr.t("message.files", cuenta=len(manifiesto.files)))
    for f in manifiesto.files:
        print(tr.t("message.file_entry", accion=f.action, ruta=f.path,
                   tamano=f.size))
    return SALIDA_BIEN


# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    """Entry point for the Vitruvio CLI."""
    if not argv or argv[0] in ("--help", "-h", "help"):
        tr = _tr()
        print(__doc__)
        return SALIDA_USO
    if argv[0] in ("--version", "-V", "version"):
        cfg = Config.cargar()
        installation_dir = Path(cfg.obtener("installation_dir", "."))
        manifiesto_path = installation_dir / "manifiesto.json"
        if manifiesto_path.is_file():
            try:
                datos = json.loads(manifiesto_path.read_text(encoding="utf-8"))
                version = datos.get("version", "desconocida")
                delivery = datos.get("entrega", "desconocido")
                print(f"Vitruvio {version} ({delivery})")
            except (json.JSONDecodeError, OSError):
                from . import __version__
                print(f"Vitruvio {__version__}")
        else:
            from . import __version__
            print(f"Vitruvio {__version__}")
        return SALIDA_BIEN

    verbo = argv[0]
    if verbo in SINONIMOS:
        verbo = SINONIMOS[verbo]

    if verbo not in ACCIONES:
        tr = _tr()
        print(tr.t("error.unknown_command", orden=verbo))
        print(tr.t("app.run_help"))
        return SALIDA_USO

    resto = argv[1:]

    # Load configuration once.
    cfg = Config.cargar()
    tr = _tr(cfg)

    if verbo == "config":
        return manejar_config(resto, cfg, tr)

    if verbo == "install":
        return _cmd_install(resto, cfg)

    if verbo == "verify":
        return _cmd_verify(resto, cfg)

    if verbo == "undo":
        return _cmd_undo(resto, cfg)

    if verbo == "history":
        return _cmd_history(resto, cfg)

    if verbo == "clean":
        return _cmd_clean(resto, cfg)

    if verbo == "inspect":
        return _cmd_inspect(resto, cfg)

    # Should not reach here.
    tr = _tr(cfg)
    print(tr.t("app.unknown_command", orden=verbo))
    print(tr.t("app.run_help"))
    return SALIDA_USO
