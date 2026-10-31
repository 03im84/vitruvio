# Vitruvio — Manual de Usuario

Vitruvio es un instalador universal con deshacer y verificación. Lee un paquete de entrega (ZIP + manifiesto + diseño), lo instala en una carpeta de destino, guarda un registro de lo que hizo y puede verificarlo o deshacerlo.

Todo por terminal. Nada de interfaz gráfica.

---

## 1. Empezar en tres órdenes

```bash
# Ver la ayuda general
python vitruvio.py --help

# Ver la versión instalada
python vitruvio.py --version

# Inspeccionar un paquete antes de instalar
python vitruvio.py inspect paquete.zip
```

> En Windows, usa `py` en lugar de `python`: `py vitruvio.py --help`

---

## 2. Comandos disponibles

| Comando | Uso | Qué hace |
|---------|-----|----------|
| `install` | `install PAQUETE.zip --destiny CARPETA` | Instala el paquete en `CARPETA` |
| `verify` | `verify --destiny CARPETA` | Comprueba que la instalación esté intacta |
| `undo` | `undo --destiny CARPETA --confirmation-from-file ARCHIVO` | Deshace la última instalación |
| `history` | `history --destiny CARPETA` | Muestra el historial de instalaciones |
| `clean` | `clean [MB] --destiny CARPETA` | Limpia archivos temporales y antiguos |
| `inspect` | `inspect PAQUETE.zip` | Muestra el contenido del paquete sin instalar |
| `config` | `config view` / `config set CLAVE VALOR` | Gestiona la configuración de Vitruvio |

Todos los comandos, parámetros y flags están **siempre en inglés**.

---

## 3. Instalar un paquete

```bash
python vitruvio.py install mi-entrega.zip --destiny ./mi-app
```

Esto hará lo siguiente:

1. Lee `mi-entrega.zip` y su `manifiesto.json` interno.
2. Verifica la huella SHA-256 de cada archivo.
3. Desempaqueta los archivos en `./mi-app`.
4. Registra la operación en un archivo de recibo (`receipt.json`).
5. Si algo falla, no deja el sistema a medias.

---

## 4. Verificar una instalación

```bash
python vitruvio.py verify --destiny ./mi-app
```

Comprueba que todos los archivos instalados coincidan con las huellas del manifiesto. Si algún archivo fue modificado o falta, lo reporta.

---

## 5. Deshacer una instalación

```bash
python vitruvio.py undo --destiny ./mi-app --confirmation-from-file receipt.json
```

Elimina los archivos que Vitruvio instaló en `./mi-app` según el registro guardado. Solo deshace lo que Vitruvio hizo; no toca otros archivos que ya estuvieran en la carpeta.

---

## 6. Configuración

Ver la configuración actual:

```bash
python vitruvio.py config view
```

Establecer una opción (las claves están en inglés):

```bash
python vitruvio.py config set language en
python vitruvio.py config set theme oscuro
```

---

## 7. Idioma y tema

Vitruvio soporta dos idiomas para los mensajes de pantalla:

- `es` — español (por defecto)
- `en` — inglés

Cambiar idioma:

```bash
python vitruvio.py config set language en
```

Los temas de color disponibles dependen de la entrega instalada. Los más comunes son: `oscuro`, `claro`, `sepia`.

---

## 8. Principios que respeta Vitruvio

| Principio | Qué significa |
|-----------|---------------|
| **D-84** | Nunca guarda contraseñas |
| **D-91** | Todo por terminal, nada de GUI |
| Claves en inglés | Comandos, parámetros y flags siempre en inglés |
| UI localizable | Solo los mensajes de pantalla se traducen (es|en) |
| Config portable | La configuración vive junto a la aplicación, nunca en `~/.config/` |

---

## 9. Ejemplo completo

```bash
# 1. Inspeccionar el paquete
python vitruvio.py inspect entrega-v1.zip

# 2. Instalar en una carpeta propia
python vitruvio.py install entrega-v1.zip --destiny ~/mi-aplicacion

# 3. Verificar que todo esté bien
python vitruvio.py verify --destiny ~/mi-aplicacion

# 4. Si algo salió mal, deshacer
python vitruvio.py undo --destiny ~/mi-aplicacion --confirmation-from-file ~/mi-aplicacion/.vitruvio/receipt.json
```

---

¿Necesitas ayuda? Ejecuta `python vitruvio.py --help` o `python vitruvio.py config help`.
