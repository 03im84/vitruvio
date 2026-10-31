"""Generador de maquetas de la CLI de Muelle. Herramienta de diseño, no producto."""
import html as html_mod
import json
import re
from pathlib import Path

ANCHO = 100
MARCA = re.compile(r"\{([a-z_]+)\|((?:[^{}]|\{[^|}]*\})*)\}")

TEMAS, FONDOS, FONDOS_TOKEN = {}, {}, {}
FUENTES_TEMA = [
    ("/home/user/muelle/resources/themes/%s.json", ("oscuro", "claro", "sepia")),
    ("/home/user/docs/propuestas/temas/%s.json",
     ("alto_contraste", "daltonico", "fosforo", "ambar", "blanco_calido",
      "verde_apagado", "fosforo_color")),
]
for patron, nombres in FUENTES_TEMA:
    for nombre in nombres:
        datos = json.loads(Path(patron % nombre).read_text(encoding="utf-8"))
        TEMAS[nombre] = {k: "rgb(%d,%d,%d)" % tuple(v["rgb"]) for k, v in datos["tokens"].items()}
        FONDOS[nombre] = tuple(datos["fondo"]["rgb"]) if "fondo" in datos else None
        FONDOS_TOKEN[nombre] = {k: tuple(v["fondo"]) for k, v in datos["tokens"].items() if "fondo" in v}

def visible(texto):
    return len(MARCA.sub(lambda m: m.group(2), texto))

def rellenar(texto, ancho):
    sobra = visible(texto) - ancho
    if sobra > 0:
        raise SystemExit("DESBORDE de %d columnas en: %r" % (sobra, MARCA.sub(lambda m: m.group(2), texto)))
    return texto + " " * (ancho - visible(texto))

def col(texto, ancho, tok="valor", derecha=False):
    """Una celda de ancho exacto: recorta si no cabe, para que la maqueta no mienta."""
    plano = MARCA.sub(lambda m: m.group(2), texto)
    if len(plano) > ancho:
        plano = plano[: max(0, ancho - 1)] + "…"
        texto = "{%s|%s}" % (tok, plano)
    hueco = " " * (ancho - len(plano))
    return (hueco + texto) if derecha else (texto + hueco)

def cel(texto, ancho, tok, derecha=False):
    """Celda cuyo relleno TAMBIÉN va pintado. Imprescindible para que la fila
    elegida sea una barra continua y no un reguero de parches."""
    plano = MARCA.sub(lambda m: m.group(2), texto)
    if len(plano) > ancho:
        plano = plano[: max(0, ancho - 1)] + "…"
    hueco = " " * (ancho - len(plano))
    return "{%s|%s}" % (tok, (hueco + plano) if derecha else (plano + hueco))

def linea_suelta(texto, ancho=ANCHO):
    return rellenar(texto, ancho)

def caja(indice, titulo, filas, ancho=ANCHO, glifos="unicode"):
    if glifos == "unicode":
        es, ed, ii, id_, h, v = "┌", "┐", "└", "┘", "─", "│"
    else:
        es = ed = ii = id_ = "+"; h = "-"; v = "|"
    cabecera = "%s%s%s%s " % (h, "{acento|" + indice + "}" if indice else "", "{titulo|" + titulo + "}", "")
    linea = es + h + ("{acento|%s}" % indice if indice else "") + "{titulo|%s}" % titulo
    resto = ancho - 2 - 1 - len(indice) - len(titulo)
    linea += "{borde|%s}" % (h * resto) + ed
    salida = ["{borde|%s}" % es + "{borde|%s}" % h + ("{acento|%s}" % indice if indice else "")
              + "{titulo|%s}" % titulo + "{borde|%s}" % (h * resto) + "{borde|%s}" % ed]
    for fila in filas:
        salida.append("{borde|%s}%s{borde|%s}" % (v, rellenar(fila, ancho - 2), v))
    salida.append("{borde|%s}%s{borde|%s}" % (ii, h * (ancho - 2), id_))
    return salida

def juntar(*bloques):
    """Pone cajas una al lado de otra."""
    altura = max(len(b) for b in bloques)
    filas = []
    for i in range(altura):
        trozos = []
        for b in bloques:
            trozos.append(b[i] if i < len(b) else " " * visible(b[0]))
        filas.append("".join(trozos))
    return filas

# ───────────────────────────── M1 · PANEL EN VIVO ─────────────────────────────
def panel_vivo():
    L = []
    L.append(linea_suelta(" " + col("{resaltado|muelle 0.3.0}  {tenue|comparte una carpeta}", 60)
             + col("{tenue|14:32}   {exito|●}{texto| 3 conexiones}   {aviso|○ sin cifrado}", 39, derecha=True)))
    L += caja("¹", "servidor", [
        " " + col("{valor|ftp://192.168.1.50:2121}", 26)
        + col("{tenue|en marcha desde las 13:58 · 34 min}", 39)
        + col("{etiqueta|Subiendo} {exito|▂▃▅▇▆▄▂▃▅▆▇▅}  {valor|1,8 MB/s}", 32),
        " " + col("{etiqueta|Carpeta}  {valor|/home/ana/Compartido}", 65)
        + col("{etiqueta|Bajando}  {acento|▁▁▂▂▁▃▂▁▁▂▁▁}  {valor|0,4 MB/s}", 32),
        " " + col("{etiqueta|Espacio}  {barra_llena|████████████}{barra_vacia|░░░░░░░░}  {valor|58 %}"
                  "  {tenue|·}  {valor|21,4 GB libres}", 65)
        + col("{etiqueta|Hoy}  {valor|1,2 GB} {tenue|↑ ·} {valor|340 MB} {tenue|↓}", 32),
    ])
    izq = caja("²", "gente", [
        " {exito|●} {valor|ana}      {tenue|conectada}",
        " {exito|●} {valor|luis}     {tenue|conectada}",
        " {exito|●} {valor|carmen}   {tenue|conectada}",
        " {tenue|○} {tenue|dani}     {tenue|sin entrar}",
    ], ancho=30)
    cen = caja("³", "avisos", [
        " {aviso|⚠} {texto|Nadie cifra la conexión}",
        " {aviso|⚠} {texto|2 contraseñas falladas}",
        "   {tenue|(desde 192.168.1.90)}",
        " {exito|✓} {texto|Carpeta y permisos bien}",
    ], ancho=36)
    der = caja("⁴", "puertas", [
        " {etiqueta|Control}  {valor|2121}   {exito|abierto}",
        " {etiqueta|Datos}    {valor|50000-50050}",
        " {etiqueta|En uso}   {valor|3 de 51}",
        " {etiqueta|Red}      {valor|local (LAN)}",
    ], ancho=34)
    L += juntar(izq, cen, der)
    L += caja("⁵", "conexiones", [
        "   " + col("{etiqueta|Quién}", 9) + col("{etiqueta|Equipo}", 16) + col("{etiqueta|Qué hace}", 14)
        + col("{etiqueta|Archivo}", 25) + col("{etiqueta|Avance}", 16) + col("{etiqueta|Velocidad}", 10)
        + col("{etiqueta|Rato}", 4) + " ",
        cel(" ▶ ", 3, "resaltado") + cel("ana", 9, "resaltado") + cel("192.168.1.23", 16, "resaltado")
        + cel("subiendo", 14, "resaltado") + cel("vacaciones/DSC_0421.jpg", 25, "resaltado")
        + cel("███████░░░ 68 %", 16, "resaltado") + cel("1,4 MB/s", 10, "resaltado")
        + cel("0:12", 4, "resaltado") + cel(" ", 1, "resaltado"),
        "   " + col("{valor|luis}", 9) + col("{valor|192.168.1.41}", 16) + col("{valor|descargando}", 14)
        + col("{valor|informe-anual.pdf}", 25)
        + col("{barra_llena|██}{barra_vacia|░░░░░░░░} {valor|19 %}", 16)
        + col("{valor|0,4 MB/s}", 10) + col("{valor|0:31}", 4) + " ",
        "   " + col("{valor|carmen}", 9) + col("{valor|192.168.1.17}", 16) + col("{valor|mirando}", 14)
        + col("{tenue|/fotos}", 25) + col("{tenue|—}", 16) + col("{tenue|—}", 10) + col("{valor|2:05}", 4) + " ",
    ])
    L += caja("", "ana · 192.168.1.23 · entró a las 14:19", [
        " " + col("{etiqueta|Permisos}  {valor|subir y descargar}", 40)
        + col("{etiqueta|Su carpeta}  {valor|/home/ana/Compartido/ana}", 57),
        " {etiqueta|Lo último}  {tenue|(6 acciones en 48 s)}",
        "   " + col("{exito|✓} {texto|Subió}", 12) + col("{valor|vacaciones/DSC_0418.jpg}", 26)
        + col("{exito|████████████████}", 36) + col("{tenue|4,2 MB}", 9) + col("{tenue|8,1 s}", 10),
        "   " + col("{exito|✓} {texto|Subió}", 12) + col("{valor|vacaciones/DSC_0419.jpg}", 26)
        + col("{exito|███████████}", 36) + col("{tenue|3,1 MB}", 9) + col("{tenue|5,4 s}", 10),
        "   " + col("{exito|✓} {texto|Miró}", 12) + col("{valor|/vacaciones}", 26)
        + col("{acento|▏}", 36) + col("{tenue|—}", 9) + col("{tenue|0,1 s}", 10),
        "   " + col("{acento|◆} {texto|Subiendo}", 12) + col("{valor|vacaciones/DSC_0421.jpg}", 26)
        + col("{acento|███████▌}", 36) + col("{tenue|2,8 MB}", 9) + col("{acento|en curso}", 10),
    ])
    L.append(linea_suelta(" " + col("{tenue|↑↓} {texto|elegir}  {tenue|c} {texto|cerrar conexión}  "
             "{tenue|/} {texto|filtrar}  {tenue|r} {texto|registro}  {tenue|t} {texto|tema}  "
             "{tenue|+−} {texto|tamaño}  {tenue|p} {texto|pausar}  {tenue|q} {texto|salir}", 89)
             + col("{tenue|cada 1 s}", 10, derecha=True)))
    return L

# ─────────────────── M2 · DEGRADACIÓN: 80 COLUMNAS Y SIN UNICODE ───────────────────
def panel_ascii():
    A = 80
    L = [linea_suelta(" " + col("muelle 0.3.0 - comparte una carpeta", 43)
                      + col("14:32  3 conexiones  sin cifrado", 36, derecha=True), A)]
    L += caja("1.", "servidor", [
        " ftp://192.168.1.50:2121    en marcha desde las 13:58 (34 min)",
        " Carpeta  /home/ana/Compartido",
        " Espacio  [############........]  58 %  ·  21,4 GB libres",
        " Subiendo 1,8 MB/s   Bajando 0,4 MB/s   Hoy 1,2 GB subidos / 340 MB bajados",
    ], ancho=A, glifos="ascii")
    L += caja("2.", "conexiones", [
        "   Quien    Equipo         Que hace      Archivo              Avance    Rato",
        " > ana      192.168.1.23   subiendo      DSC_0421.jpg         68 %      0:12",
        "   luis     192.168.1.41   descargando   informe-anual.pdf    19 %      0:31",
        "   carmen   192.168.1.17   mirando       /fotos               -         2:05",
    ], ancho=A, glifos="ascii")
    L.append(linea_suelta(" flechas elegir   c cerrar conexion   / filtrar   t tema   +- tamano"
                          "   q salir", A))
    return L

# ─────────────────────── M3 · ASISTENTE DE PRIMERA VEZ ───────────────────────
def asistente():
    L = []
    L += caja("", "primera vez · paso 2 de 4", [
        " {barra_llena|████████████████████████}{barra_vacia|████████████████████████████████████████████████}  {tenue|50 %}",
        "",
        " {titulo|¿Qué carpeta quieres compartir?}",
        "",
        " {tenue|Escribe una ruta o pulsa Enter para aceptar la propuesta.}",
        "",
        "   {acento|>} {valor|/home/ana/Compartido}{tenue|▏}",
        "",
        " {exito|✓} {texto|La carpeta existe y puedes escribir en ella.}",
        " {tenue|  Dentro hay 128 archivos (2,4 GB).}",
        "",
    ])
    L.append(linea_suelta(" " + col("{tenue|Enter} {texto|aceptar}    {tenue|Ctrl+C} {texto|salir sin cambiar nada}", 55)
             + col("{tenue|paso 1} {exito|✓} {tenue|· paso 2 · paso 3 · paso 4}", 44, derecha=True)))
    return L

# ─────────────────── M4 · INSTALAR UNA ENTREGA (paquete ZIP) ───────────────────
def instalar():
    L = []
    L += caja("", "instalar · muelle-0.3.0.zip", [
        " {etiqueta|Paquete}   {valor|muelle-0.3.0.zip}   {tenue|138 KB · 58 archivos}",
        " {etiqueta|Destino}   {valor|/opt/muelle}        {tenue|versión actual: 0.2.0}",
        "",
        " {exito|✓} {texto|El paquete se abre y no trae sorpresas}   {tenue|(sin enlaces, sin rutas raras, 58 de 10 000)}",
        " {exito|✓} {texto|Cada archivo coincide con su firma}       {tenue|(58 de 58 comprobados)}",
        " {exito|✓} {texto|Copia de seguridad de lo que se sustituye}{tenue| (24 archivos guardados)}",
        " {acento|◆} {texto|Copiando archivos}                        {barra_llena|█████████████}{barra_vacia|███████}  {valor|41 de 58}",
        " {tenue|○} {tenue|Comprobar la instalación}",
        " {tenue|○} {tenue|Guardar el recibo}",
        "",
        " {tenue|Si algo sale mal, nada queda a medias: se deshace solo y te lo cuenta.}",
    ])
    L.append("")
    L += caja("", "instalar · terminado", [
        " {exito|✓} {texto|Muelle 0.3.0 instalado.}  {tenue|34 archivos nuevos · 24 sustituidos · 0 borrados}",
        "",
        " {etiqueta|Recibo}   {valor|/opt/muelle/.muelle/recibos/0.3.0.json}",
        " {etiqueta|Copias}   {valor|/opt/muelle/.muelle/copias/2026-10-21-1432/}",
        "",
        " {tenue|Para volver a la versión anterior en cualquier momento:}  {acento|muelle deshacer}",
    ])
    return L

# ─────────────────────────── M5 · DESHACER (ROLLBACK) ───────────────────────────
def deshacer():
    L = []
    L += caja("", "deshacer la última instalación", [
        " {etiqueta|Se instaló}   {valor|muelle 0.3.0}   {tenue|hoy a las 14:32 (hace 6 min)}",
        " {etiqueta|Recibo}       {valor|0.3.0.json}    {tenue|comprobado: coincide con lo que hay en disco}",
        "",
        " {texto|Esto va a}",
        "   {texto|· devolver} {valor|24 archivos} {texto|a como estaban}",
        "   {texto|· quitar}   {valor|34 archivos} {texto|que trajo esta versión}",
        "   {texto|· borrar}   {valor|muelle-0.3.0.zip} {tenue|(solo ese, en su sitio y con su firma)}",
        "",
        " {aviso|⚠} {texto|Tus ajustes, usuarios y archivos compartidos no se tocan.}",
        "",
        " {texto|Escribe}  {resaltado|DESHACER}  {texto|para confirmar:}  {acento|>} {tenue|▏}",
    ])
    L.append("")
    L += caja("", "deshacer · hecho", [
        " {exito|✓} {texto|Vuelves a tener la versión 0.2.0, tal y como estaba.}",
        " {tenue|  24 archivos devueltos · 34 quitados · paquete rechazado borrado}",
        "",
        " {etiqueta|Informe}  {valor|/opt/muelle/.muelle/recibos/0.3.0-deshecho.json}",
    ])
    L.append("")
    L += caja("", "deshacer · cuando NO se puede", [
        " {error|✖} {texto|Alguien tocó 3 de los archivos después de instalar.}",
        "",
        " {etiqueta|Qué puedes hacer}",
        "   {texto|Guarda una copia de esos tres y vuelve a intentarlo:}",
        "   {tenue|muelle/ui/render.py · muelle/api.py · config.json}",
        "",
        " {tenue|No se ha tocado nada. Deshacer solo actúa si está todo como lo dejó.}",
    ])
    return L


# ─────────────────────── M7 · TAMAÑO DE LA INTERFAZ ───────────────────────
GLIFOS = {
    "0": ("███", "█ █", "█ █", "█ █", "███"), "1": ("  █", "  █", "  █", "  █", "  █"),
    "2": ("███", "  █", "███", "█  ", "███"), "3": ("███", "  █", "███", "  █", "███"),
    "4": ("█ █", "█ █", "███", "  █", "  █"), "5": ("███", "█  ", "███", "  █", "███"),
    "6": ("███", "█  ", "███", "█ █", "███"), "7": ("███", "  █", "  █", "  █", "  █"),
    "8": ("███", "█ █", "███", "█ █", "███"), "9": ("███", "█ █", "███", "  █", "███"),
    "%": ("█ █", "  █", " █ ", "█  ", "█ █"), ",": ("   ", "   ", "   ", "  █", " █ "),
    " ": ("   ", "   ", "   ", "   ", "   "),
}

def cifra_grande(texto):
    """Las cinco filas de una cifra dibujada con bloques (modo gigante)."""
    filas = ["", "", "", "", ""]
    for caracter in texto:
        glifo = GLIFOS.get(caracter, GLIFOS[" "])
        for i in range(5):
            filas[i] += glifo[i] + " "
    return [f[:-1] for f in filas]

def tamanos():
    L = []
    L.append(linea_suelta(" {texto|Tu terminal manda en la fuente: ningún programa puede agrandarla igual"
                          " en Linux, Windows y macOS.}"))
    L.append(linea_suelta(" {texto|Lo que Muelle sí decide es cuánto sitio ocupa cada cosa. Cuatro tamaños,"
                          " la misma información.}"))
    L.append("")
    L += caja("1 ", "compacto · cabe en 24 líneas × 80 columnas (consola de servidor, portátil pequeño)", [
        " " + col("{valor|ftp://192.168.1.50:2121}", 26)
        + col("{exito|●} {valor|3} {tenue|conexiones}", 17) + col("{valor|58 %} {tenue|disco}", 12)
        + col("{valor|↑1,8}{tenue| MB/s}  {valor|↓0,4}{tenue| MB/s}", 23)
        + col("{tenue|34 min en marcha}", 19),
        " " + col("{acento|▶} {valor|ana} {tenue|sube} {valor|DSC_0421.jpg} {resaltado|68 %}", 34)
        + col("{valor|luis} {tenue|baja} {valor|informe.pdf} {valor|19 %}", 33)
        + col("{valor|carmen} {tenue|mira} {tenue|/fotos}", 30),
    ])
    L.append("")
    L += caja("2 ", "normal · el de la maqueta M1; lo que verás casi siempre", [
        " " + col("{etiqueta|Carpeta}  {valor|/home/ana/Compartido}", 48)
        + col("{etiqueta|Subiendo} {exito|▂▃▅▇▆▄▂▃▅▆▇▅}  {valor|1,8 MB/s}", 49),
        " " + col("{etiqueta|Espacio}  {barra_llena|████████████}{barra_vacia|░░░░░░░░}  {valor|58 %}", 48)
        + col("{etiqueta|Bajando}  {acento|▁▁▂▂▁▃▂▁▁▂▁▁}  {valor|0,4 MB/s}", 49),
    ])
    L.append("")
    L += caja("3 ", "amplio · una cosa por línea y más aire; para quien lee de lejos", [
        "",
        "   " + col("{etiqueta|Espacio del disco}", 22)
        + col("{barra_llena|██████████████████████████}{barra_vacia|██████████████████}", 46)
        + col("{resaltado|58 %}", 26),
        "",
        "   " + col("{etiqueta|Subiendo ahora}", 22) + col("{exito|▂▃▅▇▆▄▂▃▅▆▇▅▇▆▄▂▃▅}", 46)
        + col("{resaltado|1,8 MB/s}", 26),
        "",
    ])
    L.append("")
    izq = cifra_grande("58%")
    der = cifra_grande("1,8")
    etiq_izq = ["", "{etiqueta|del disco en uso}", "{tenue|21,4 GB libres}", "", ""]
    etiq_der = ["", "{etiqueta|MB/s subiendo}", "{tenue|0,4 MB/s bajando}", "", ""]
    filas = []
    for i in range(5):
        filas.append("  " + col("{barra_llena|%s}" % izq[i], 13) + col(etiq_izq[i], 32)
                     + col("{acento|%s}" % der[i], 13) + col(etiq_der[i], 38))
    L += caja("4 ", "gigante · un dato cada vez, en cifras de bloque; se lee desde la otra punta", filas)
    L.append("")
    L.append(linea_suelta(" {etiqueta|Se cambia}  {valor|+} {texto|y} {valor|−} {tenue|en el panel}"
                          "  {tenue|·}  {valor|muelle panel --tamano gigante}"
                          "  {tenue|·}  {valor|interfaz.escala} {tenue|en config.json}"))
    L.append(linea_suelta(" {etiqueta|No hacemos}  {texto|tocar la fuente de tu terminal a tus espaldas:"
                          " ahí mandas tú} {tenue|(Ctrl y + en casi todas)}{texto|.}"))
    return L


# ─────────────── M8 · TEMAS DE TERMINAL CLÁSICA (sesión de verdad) ───────────────
def sesion():
    """Una sesión corriente que toca todos los papeles del color: indicador,
    orden, carpetas, texto, error y selección."""
    L = []
    A = lambda s: L.append(linea_suelta(s))
    A(" {acento|ana@nave}{tenue|:}{acento|~/Compartido}{tenue|$} {valor|muelle compartir . --puerto 2121}")
    A(" {exito|✓} {texto|Listo. Tu carpeta ya se ve desde la red:}  {titulo|ftp://192.168.1.50:2121}")
    A(" {tenue|Déjalo abierto mientras lo uséis. Para pararlo: muelle parar}")
    A("")
    A(" {acento|ana@nave}{tenue|:}{acento|~/Compartido}{tenue|$} {valor|muelle gente}")
    A("   " + col("{etiqueta|Quién}", 10) + col("{etiqueta|Equipo}", 16)
      + col("{etiqueta|Puede}", 22) + col("{etiqueta|Entró}", 10) + col("{etiqueta|Ahora}", 39))
    A(" {exito|●} " + col("{texto|ana}", 10) + col("{texto|192.168.1.23}", 16)
      + col("{texto|subir y descargar}", 22) + col("{tenue|14:19}", 10)
      + col("{texto|subiendo DSC_0421.jpg}", 39))
    A(" {exito|●} " + col("{texto|luis}", 10) + col("{texto|192.168.1.41}", 16)
      + col("{texto|solo descargar}", 22) + col("{tenue|14:02}", 10)
      + col("{texto|bajando informe-anual.pdf}", 39))
    A(" {tenue|○} " + col("{tenue|dani}", 10) + col("{tenue|—}", 16)
      + col("{tenue|solo descargar}", 22) + col("{tenue|—}", 10) + col("{tenue|sin entrar hoy}", 39))
    A("")
    A(" {acento|ana@nave}{tenue|:}{acento|~/Compartido}{tenue|$} {valor|muelle carpeta}")
    A("   " + col("{titulo|vacaciones/}", 26) + col("{tenue|34 archivos}", 14)
      + col("{tenue|1,2 GB}", 12) + col("{tenue|modificada hoy a las 14:28}", 45))
    A("   " + col("{titulo|informes/}", 26) + col("{tenue|8 archivos}", 14)
      + col("{tenue|46 MB}", 12) + col("{tenue|modificada ayer}", 45))
    A("   " + col("{texto|informe-anual.pdf}", 26) + col("{tenue|—}", 14)
      + col("{tenue|4,1 MB}", 12) + col("{tenue|modificado el 12 de octubre}", 45))
    A("")
    A(" {acento|ana@nave}{tenue|:}{acento|~/Compartido}{tenue|$} {valor|muelle compartir /raiz}")
    A(" {error|✗ No puedo compartir esa carpeta: el sistema no me deja leerla.}")
    A("   {texto|Pruebe con una carpeta suya, por ejemplo} {valor|~/Compartido}{texto|.}")
    A("")
    A(" {acento|ana@nave}{tenue|:}{acento|~/Compartido}{tenue|$} {valor|muelle panel}")
    A(" {tenue|(la fila elegida se ve así)}")
    L.append(linea_suelta(" " + cel(" ▶ ana · 192.168.1.23 · subiendo vacaciones/DSC_0421.jpg · 68 % · 1,4 MB/s", 80, "resaltado")
                          + col("{tenue|↑↓ elegir}", 19)))
    return L

# ─────────────────────── RENDER A TERMINAL (texto y ANSI) ───────────────────────
RGB = re.compile(r"rgb\((\d+),(\d+),(\d+)\)")

def a_ansi(lineas, tema, ancho=None):
    """Pinta con la paleta real. Si el tema trae fondo, se pinta la línea entera:
    que es lo que hará el panel al tomar la pantalla alternativa."""
    pal = TEMAS[tema]
    fondo = FONDOS.get(tema)
    por_token = FONDOS_TOKEN.get(tema, {})
    pagina = "\x1b[48;2;%d;%d;%dm" % fondo if fondo else ""
    ancho = ancho or ANCHO
    salida = []
    for linea in lineas:
        pos, trozos = 0, [pagina]
        for m in MARCA.finditer(linea):
            trozos.append(linea[pos:m.start()])
            tok = m.group(1)
            r, g, b = RGB.match(pal.get(tok, pal["texto"])).groups()
            negrita = "1;" if tok in ("titulo", "resaltado") else ""
            propio = "\x1b[48;2;%d;%d;%dm" % por_token[tok] if tok in por_token else ""
            trozos.append("%s\x1b[%s38;2;%s;%s;%sm%s\x1b[0m%s"
                          % (propio, negrita, r, g, b, m.group(2), pagina))
            pos = m.end()
        trozos.append(linea[pos:])
        if fondo:
            trozos.append(" " * max(0, ancho - visible(linea)))
            trozos.append("\x1b[0m")
        salida.append("".join(trozos))
    return "\n".join(salida)

def a_texto(lineas):
    return "\n".join(MARCA.sub(lambda m: m.group(2), l).rstrip() for l in lineas)

PANTALLAS = [
    ("M1 · Panel en vivo", "muelle panel", "La pantalla principal: una ojeada y sabes qué está pasando. "
     "Paneles numerados, tabla con la fila elegida y detalle de esa fila debajo.", panel_vivo()),
    ("M2 · La misma pantalla en una terminal pobre", "muelle panel   (80 columnas, sin Unicode, sin color)",
     "Mismo contenido, misma jerarquía, cero adornos: se degrada con elegancia.", panel_ascii()),
    ("M3 · Asistente de primera vez", "muelle   (sin configurar)",
     "Cuatro pasos, una pregunta por pantalla, siempre con una propuesta aceptable pulsando Enter.", asistente()),
    ("M4 · Instalar una entrega", "herramientas/instalar.py  muelle-0.3.0.zip",
     "Verificar antes de tocar nada, copia de seguridad, recibo al final.", instalar()),
    ("M5 · Deshacer la instalación", "herramientas/instalar.py  --deshacer",
     "Vuelta atrás con confirmación escrita, borrado del ZIP rechazado y negativa segura si algo cambió.", deshacer()),
    ("M7 · Tamaño de la interfaz", "muelle panel --tamano compacto | normal | amplio | gigante",
     "Cuatro escalas de la misma pantalla, porque la fuente del terminal no es nuestra.", tamanos()),
]

AVISO = [
    "MUELLE · MAQUETAS DE LA INTERFAZ",
    "Propuesta visual · fase 2 · NADA DE ESTO ESTÁ IMPLEMENTADO",
    "",
    "Muelle es una herramienta de línea de órdenes. No hay, ni habrá, interfaz web:",
    "lo que ves aquí es exactamente lo que se dibuja en una terminal de texto.",
    "",
    "Las pantallas están generadas con la geometría real (100 columnas, 80 en el modo",
    "pobre) y con la paleta real de muelle/resources/themes/*.json, así que lo que",
    "cabe aquí es lo que cabe allí.",
    "",
    "   maquetas en texto plano   docs/07_MAQUETAS_CLI.txt",
    "   maquetas en color         cat docs/07_MAQUETAS_CLI.ans   (en tu terminal)",
    "   quien las dibuja          docs/propuestas/generador_maquetas.py",
    "",
    "Revisión 2 (21-10-2026): maquetas M1-M5 aprobadas. Esta revisión añade M7 (tamaño de la",
    "interfaz) y amplía M6 (temas) a petición tuya. M7 y los dos temas nuevos están pendientes",
    "de aprobación.",
    "",
]

texto = list(AVISO)
ansi = []
for i, l in enumerate(AVISO):
    tok = "titulo" if i == 0 else ("aviso" if i == 1 else "tenue")
    ansi.append(a_ansi(["{%s|%s}" % (tok, l)] if l else [""], "oscuro"))

for titulo, orden, nota, lineas in PANTALLAS:
    regla = "─" * ANCHO
    for destino, pintar in ((texto, False), (ansi, True)):
        bloque = [regla, titulo, "$ " + orden, nota, regla, ""]
        if pintar:
            destino.append(a_ansi(["{borde|%s}" % regla, "{titulo|%s}" % titulo, "{acento|$ %s}" % orden,
                                   "{tenue|%s}" % nota, "{borde|%s}" % regla, ""], "oscuro"))
            destino.append(a_ansi(lineas, "oscuro"))
            destino.append("")
        else:
            destino.extend(bloque)
            destino.append(a_texto(lineas))
            destino.append("")

# ── M6 · Temas: cargador, no lista cerrada ──
M6_TEXTO = [
    "─" * ANCHO,
    "M6 · Temas",
    "Muelle no trae «un tema»: trae un cargador de temas. Cada tema es un JSON de 13 colores; añadir",
    "uno es copiar un fichero en la carpeta, sin tocar una línea de código.",
    "─" * ANCHO,
    "",
    "  Obligatorios (mandato G-07)      muelle/resources/themes/",
    "    oscuro           terminal de fondo oscuro, el de toda la vida",
    "    claro            fondo blanco, para trabajar con luz natural de frente",
    "    sepia            lectura larga: menos azul, menos contraste, menos cansancio",
    "",
    "  Propuestos ahora (pendientes de tu visto bueno)   docs/propuestas/temas/",
    "    alto_contraste   baja visión, proyectores y pantallas con reflejos: todo negrita, contraste máximo",
    "    daltonico        daltonismo rojo-verde (~8 % de los hombres): bien y mal se distinguen por azul",
    "                     frente a naranja, y además por símbolo, nunca solo por color",
    "",
    "  Tuyos",
    "    mi_tema.json     cualquier fichero que dejes en la carpeta sale en «t tema» y en config.json",
    "",
    "  Cuando el terminal no da para tanto, el tema no se apaga: se traduce.",
    "    color verdadero  la paleta tal cual, 24 bits                      [ya implementado]",
    "    16 colores       el código «basico» que cada token lleva escrito  [ya implementado]",
    "    sin color        negrita, subrayado y símbolos (✓ ⚠ ✗ ▶) hacen el trabajo del color  [implementado]",
    "    256 colores      el más parecido de la paleta de 256             [mejora propuesta]",
    "    sin Unicode      marcos con +-| y barras con [####....]          [ya implementado, maqueta M2]",
    "",
    "  En texto plano los cinco temas se ven idénticos: ese es justo el punto del modo sin color.",
    "  Para verlos de verdad:   cat docs/07_MAQUETAS_CLI.ans",
    "",
]
texto.extend(M6_TEXTO)

ansi.append(a_ansi(["{borde|%s}" % ("─" * ANCHO), "{titulo|M6 · Temas}",
                    "{tenue|Tres obligatorios, dos propuestos y los que tú añadas: cada uno es un JSON de 13 colores.}",
                    "{borde|%s}" % ("─" * ANCHO), ""], "oscuro"))
ROTULOS = [
    ("oscuro", "obligatorio · fondo oscuro, el de toda la vida"),
    ("claro", "obligatorio · fondo blanco, luz natural de frente"),
    ("sepia", "obligatorio · lectura larga, menos azul"),
    ("alto_contraste", "propuesto · baja visión, proyectores, reflejos"),
    ("daltonico", "propuesto · daltonismo rojo-verde: azul frente a naranja"),
]
for tema, rotulo in ROTULOS:
    ansi.append(a_ansi(["{etiqueta|  tema %s}  {tenue|%s}" % (tema, rotulo)], "oscuro"))
    ansi.append(a_ansi(panel_vivo()[:6], tema))
    ansi.append("")

# ── M8 · Los cinco temas de terminal clásica ──
PALETAS = [
    ("fosforo",       "#33FF66", "#071A0D", "tubo de fósforo verde, el clásico de las salas de máquinas"),
    ("ambar",         "#FFB000", "#1C1000", "terminal ámbar (VT220, IBM 3279): menos azul, menos fatiga"),
    ("blanco_calido", "#E8E2C8", "#171712", "papel viejo sobre negro: neutro, sin tinte que canse"),
    ("verde_apagado", "#A8C686", "#20291B", "fósforo cansado: el verde sin gritar, para sesiones largas"),
    ("fosforo_color", "varios",  "#071A0D", "el fósforo con todos los papeles de color repartidos"),
]
M8_TEXTO = [
    "─" * ANCHO,
    "M8 · Cinco temas de terminal clásica  ·  los que me pasaste",
    "En texto plano se ven los cinco iguales. Para verlos de verdad:  cat docs/07_MAQUETAS_CLI.ans",
    "─" * ANCHO,
    "",
    "  Nombre           Tinta      Fondo      Idea",
]
for nombre, tinta, fondo, idea in PALETAS:
    M8_TEXTO.append("  %-16s %-10s %-10s %s" % (nombre, tinta, fondo, idea))
M8_TEXTO += [
    "",
    "  Los cuatro primeros son de un solo fósforo: la jerarquía se hace con BRILLO, no con tono.",
    "  tenue = tinta mezclada con el fondo · titulo/aviso/error = tinta aclarada + negrita.",
    "  Por eso existe el mandato G-24: en estos temas el color no puede ser la única señal,",
    "  y nunca lo es (✓ bien · ⚠ atención · ✗ mal · ▶ elegido · ○ inactivo).",
    "",
    "  Reparto de papeles del tema fosforo_color, tal y como lo pediste:",
    "",
    "    Lo que pediste        Token de Muelle          Color",
    "    Fondo                 fondo                    #071A0D",
    "    Texto normal          texto                    #33FF66",
    "    Prompt                acento                   #A8FFB0",
    "    Comandos              valor                    #FFB000",
    "    Directorios           titulo + exito           #66FF99",
    "    Errores               error                    #FF5C5C",
    "    Selección             resaltado                texto #E8FFE8 sobre fondo #1E6B3A",
    "",
    "  Dos cosas que esto cambia en el contrato (apéndice A de docs/04_CONTRATOS.md):",
    "    1. El tema pasa a poder traer FONDO. Hasta ahora Muelle solo ponía la tinta y respetaba",
    "       el fondo de tu terminal. Pintar el fondo solo tiene sentido en el panel, que toma la",
    "       pantalla entera; en las órdenes sueltas se seguirá respetando tu terminal.",
    "    2. Un token puede traer su propio fondo (la selección). Era necesario para tu paleta nº5.",
    "",
    "  La sesión de ejemplo, en texto plano:",
    "",
]
M8_TEXTO.append(a_texto(sesion()))
M8_TEXTO.append("")
texto.extend(M8_TEXTO)

ansi.append(a_ansi(["{borde|%s}" % ("─" * ANCHO), "{titulo|M8 · Cinco temas de terminal clásica}",
                    "{tenue|Una sesión corriente, con fondo pintado de verdad. Primero el que tiene todos los papeles de color.}",
                    "{borde|%s}" % ("─" * ANCHO), ""], "oscuro"))
ansi.append(a_ansi(["{etiqueta|  tema fosforo_color}  {tenue|tinta #33FF66 · fondo #071A0D · prompt #A8FFB0 · órdenes #FFB000 · carpetas #66FF99}"], "oscuro"))
ansi.append(a_ansi(sesion(), "fosforo_color"))
ansi.append("")
ansi.append(a_ansi(["{etiqueta|  el panel con ese mismo tema}"], "oscuro"))
ansi.append(a_ansi(panel_vivo()[:6], "fosforo_color"))
ansi.append("")
for nombre, tinta, fondo, idea in PALETAS[:4]:
    ansi.append(a_ansi(["{etiqueta|  tema %s}  {tenue|tinta %s · fondo %s · %s}" % (nombre, tinta, fondo, idea)], "oscuro"))
    ansi.append(a_ansi(sesion()[:12], nombre))
    ansi.append(a_ansi(panel_vivo()[1:6], nombre))
    ansi.append("")

Path("/home/user/docs/07_MAQUETAS_CLI.txt").write_text("\n".join(texto) + "\n", encoding="utf-8")
Path("/home/user/docs/07_MAQUETAS_CLI.ans").write_text("\n".join(ansi) + "\n", encoding="utf-8")

for titulo, _, _, lineas in PANTALLAS:
    anchos = {visible(l) for l in lineas if l.strip()}
    print("%-46s anchos: %s" % (titulo, sorted(anchos)))
