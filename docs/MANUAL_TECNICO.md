# Vitruvio — Manual Técnico

Documentación técnica para desarrolladores y mantenedores de Vitruvio.

---

## 1. Arquitectura

Vitruvio es un instalador de entregas de software escrito en Python 3. No tiene dependencias externas (solo biblioteca estándar).

```
vitruvio/
├── vitruvio.py          # Punto de entrada y orquestador de comandos
├── config.py            # Declaración de opciones de configuración
├── contract.py          # Contrato de entregas (manifiesto, firmas SHA-256)
├── layout.py            # Utilidades de rutas, huellas y listado de archivos
├── localization.py      # Internacionalización (es|en)
├── view.py              # Renderizado de paneles y salidas por terminal
├── __init__.py
├── __main__.py
└── manifiesto.json      # Manifiesto de la propia entrega de Vitruvio
```

### Flujo de ejecución

1. `vitruvio.py` parsea los argumentos de línea de comandos.
2. Carga el contexto de ejecución (`Contexto`).
3. Ejecuta la acción solicitada (`install`, `verify`, `undo`, etc.).
4. Cada acción lee el paquete ZIP, verifica firmas SHA-256 contra el manifiesto, y escribe en disco.

---

## 2. Gramática de comandos

Los comandos y flags están siempre en inglés. Se aceptan sinónimos en español como alias que se mapean al inglés canónico.

| Acción canónica | Sinónimos en español | Uso |
|-----------------|----------------------|-----|
| `install` | `instala`, `instalar` | `install PAQUETE.zip --destiny CARPETA` |
| `verify` | `comprobar`, `verificar` | `verify --destiny CARPETA` |
| `undo` | `borrar`, `deshacer` | `undo --destiny CARPETA --confirmation-from-file ARCHIVO` |
| `history` | — | `history --destiny CARPETA` |
| `clean` | `limpia`, `limpiar` | `clean [MB] --destiny CARPETA` |
| `inspect` | — | `inspect PAQUETE.zip` |
| `config` | — | `config view\|set\|validate\|where\|help` |

---

## 3. Formato del paquete de entrega

Un paquete de entrega es un archivo ZIP que contiene:

```
entrega.zip
├── manifiesto.json      # Metadatos y firmas de todos los archivos
└── <archivos del paquete>
```

### Estructura del manifiesto

```json
{
  "esquema": "manifest.v1",
  "entrega": "nombre-del-paquete",
  "version": "1.0.0",
  "fecha": "2026-10-27",
  "archivos": [
    {
      "ruta": "rutas/archivo.py",
      "firma": "sha256-hexadecimal",
      "accion": "add",
      "bytes": 1234
    }
  ]
}
```

Vitruvio verifica que cada archivo extraído coincida con su firma SHA-256 declarada en el manifiesto.

---

## 4. Configuración

Las claves de configuración están en inglés. Se almacenan en un archivo junto a la aplicación (config portable).

Claves principales:

| Clave | Tipo | Valor por defecto | Descripción |
|-------|------|-------------------|-------------|
| `app.language` | texto | `es` | Idioma de los mensajes (`es` o `en`) |
| `app.theme` | texto | `oscuro` | Tema de color de la interfaz de terminal |
| `app.color` | texto | `auto` | `auto`, `si`, `no` — forzar o desactivar colores |

---

## 5. Receipts (registros de instalación)

Cada instalación exitosa genera un archivo `receipt.json` en la carpeta de destino. Contiene:

- Lista de archivos instalados con sus rutas y huellas.
- Fecha y hora de la instalación.
- Versión del paquete instalado.

El receipt es necesario para deshacer la instalación con `undo`.

---

## 6. Principios de diseño

| Código | Principio | Implicación |
|--------|-----------|-------------|
| **D-84** | Nunca guardar contraseñas | Vitruvio no almacena ni gestiona credenciales |
| **D-91** | Todo por terminal | No hay interfaz gráfica, solo CLI |
| **D-75** | Nivel cero | Vitruvio no depende de La Groma ni de ningún otro componente externo |
| **D-76** | Tres obligaciones | Construir, verificar, asegurar (degradar, no morir) |

Vitruvio es **independiente**: no requiere que La Groma, Muelle, Hannon ni ningún otro componente estén instalados. Puede clonarse y usarse en cualquier entorno.

---

## 7. Extender Vitruvio

Para agregar una nueva acción:

1. Agrega el verbo al diccionario `ACCIONES` en `vitruvio.py`.
2. Agrega sinónimos opcionales en `SINONIMOS`.
3. Implementa la lógica de la acción.
4. Documenta la acción en `MANUAL_USUARIO.md`.

Para agregar una nueva clave de configuración:

1. Agrega el campo al esquema en `config.py`.
2. Asegura que tenga valor por defecto y validación.
3. Documenta la clave en este manual.

---

## 8. Pruebas

Los tests de Vitruvio viven en `herramientas/pruebas/`. Ejecutar:

```bash
python -m herramientas.pruebas.test_vitruvio
```

---

## 9. Versionado

Vitruvio usa versionado semántico (`MAJOR.MINOR.PATCH`). La versión actual se lee desde `vitruvio/version.py` (o equivalente) y se refleja en el manifiesto de la entrega.

---

¿Preguntas? Revisa el código fuente de `vitruvio.py` y `contract.py` para entender los detalles de implementación.
