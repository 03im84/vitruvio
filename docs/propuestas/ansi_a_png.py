"""Dibuja un trozo de terminal en PNG, carácter a carácter, a partir de ANSI.

Herramienta de diseño, no producto: sirve para que se puedan mirar los temas sin
tener que abrir una terminal. Lo que pinta son celdas de texto, no una interfaz
gráfica: es una fotografía de la terminal, nada más (mandato G-23).
"""

import importlib.util
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path("/home/user")
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_NEGRITA = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SGR = re.compile(r"\x1b\[([0-9;]*)m")


def cargar_generador():
    ruta = RAIZ / "docs/propuestas/generador_maquetas.py"
    spec = importlib.util.spec_from_file_location("gen", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def celdas(texto_ansi, fondo_defecto, tinta_defecto):
    """Convierte el ANSI en una rejilla de (carácter, tinta, fondo, negrita)."""
    filas = []
    for linea in texto_ansi.split("\n"):
        fila, tinta, fondo, negrita, pos = [], tinta_defecto, fondo_defecto, False, 0
        for m in SGR.finditer(linea):
            for caracter in linea[pos:m.start()]:
                fila.append((caracter, tinta, fondo, negrita))
            codigos = [c for c in m.group(1).split(";") if c != ""] or ["0"]
            i = 0
            while i < len(codigos):
                c = codigos[i]
                if c == "0":
                    tinta, fondo, negrita = tinta_defecto, fondo_defecto, False
                elif c == "1":
                    negrita = True
                elif c == "38" and codigos[i + 1:i + 2] == ["2"]:
                    tinta = tuple(int(x) for x in codigos[i + 2:i + 5]); i += 4
                elif c == "48" and codigos[i + 1:i + 2] == ["2"]:
                    fondo = tuple(int(x) for x in codigos[i + 2:i + 5]); i += 4
                i += 1
            pos = m.end()
        for caracter in linea[pos:]:
            fila.append((caracter, tinta, fondo, negrita))
        filas.append(fila)
    return filas


def pintar(bloques, destino, fondo_defecto=(14, 16, 22), tinta_defecto=(220, 223, 228),
           tam=16, titulo="Terminal", margen=18):
    """`bloques` es una lista de cadenas ANSI; se apilan una debajo de otra."""
    normal = ImageFont.truetype(MONO, tam)
    negrita = ImageFont.truetype(MONO_NEGRITA, tam)
    ancho_celda = round(normal.getlength("M"))
    alto_celda = round(tam * 1.42)

    rejilla = []
    for bloque in bloques:
        rejilla.extend(celdas(bloque, fondo_defecto, tinta_defecto))

    columnas = max((len(f) for f in rejilla), default=1)
    barra = alto_celda + 12
    ancho = columnas * ancho_celda + margen * 2
    alto = len(rejilla) * alto_celda + margen * 2 + barra

    imagen = Image.new("RGB", (ancho, alto), fondo_defecto)
    lienzo = ImageDraw.Draw(imagen)

    # Barra de la ventana: deja claro que esto es una terminal, no una página
    lienzo.rectangle([0, 0, ancho, barra], fill=(38, 40, 48))
    for i, color in enumerate(((237, 118, 118), (233, 196, 106), (126, 203, 143))):
        cx = 18 + i * 18
        lienzo.ellipse([cx, barra // 2 - 5, cx + 10, barra // 2 + 5], fill=color)
    lienzo.text((80, barra // 2), titulo, font=normal, fill=(150, 158, 172), anchor="lm")

    y = barra + margen
    for fila in rejilla:
        x = margen
        for caracter, tinta, fondo, gruesa in fila:
            if fondo != fondo_defecto:
                lienzo.rectangle([x, y, x + ancho_celda, y + alto_celda], fill=fondo)
            if caracter != " ":
                lienzo.text((x, y), caracter, font=negrita if gruesa else normal, fill=tinta)
            x += ancho_celda
        y += alto_celda
    imagen.save(destino)
    return destino, imagen.size


if __name__ == "__main__":
    gen = cargar_generador()
    rotulo = lambda s: gen.a_ansi(["{etiqueta|%s}" % s], "oscuro")
    hueco = ""

    # ── 1. El tema nº5, con todos los papeles de color ──
    ruta, tam = pintar(
        [gen.a_ansi(gen.sesion(), "fosforo_color"),
         hueco,
         gen.a_ansi(gen.panel_vivo(), "fosforo_color")],
        RAIZ / "docs/07_TEMA_FOSFORO_COLOR.png",
        fondo_defecto=(7, 26, 13), tinta_defecto=(51, 255, 102),
        titulo="muelle · tema fosforo_color · fondo #071A0D · tinta #33FF66")
    print("  %s  %sx%s" % (ruta.name, *tam))

    # ── 2. Los cuatro de un solo fósforo ──
    bloques = []
    for nombre, descripcion in (
        ("fosforo", "tinta #33FF66 sobre #071A0D · el clásico"),
        ("ambar", "tinta #FFB000 sobre #1C1000 · VT220"),
        ("blanco_calido", "tinta #E8E2C8 sobre #171712 · neutro"),
        ("verde_apagado", "tinta #A8C686 sobre #20291B · sin gritar"),
    ):
        bloques.append(rotulo("  tema %s — %s" % (nombre, descripcion)))
        bloques.append(gen.a_ansi(gen.sesion()[:3] + gen.sesion()[10:13] + gen.sesion()[14:18], nombre))
        bloques.append(gen.a_ansi(gen.panel_vivo()[1:6], nombre))
        bloques.append(hueco)
    ruta, tam = pintar(bloques, RAIZ / "docs/07_TEMAS_CLASICOS.png",
                       titulo="muelle · cuatro temas de un solo fósforo")
    print("  %s  %sx%s" % (ruta.name, *tam))
