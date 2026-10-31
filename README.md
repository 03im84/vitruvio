# Vitruvio

Instalador y orquestador de entregas de software.

Vitruvio lee un manifiesto de entrega, verifica las huellas SHA-256 de cada archivo y despliega la aplicación en carpetas portables.

---

## ¿Qué hace Vitruvio?

- Lee un manifiesto de entrega y verifica huellas SHA-256 de cada archivo.
- Instala la aplicación en carpetas portables junto al ejecutable.
- Genera archivos de configuración junto a la aplicación (nunca en `~/.config/`).
- Nunca guarda contraseñas (D-84).
- Todo por terminal, nada de GUI (D-91).

---

## Estructura del repositorio

```
vitruvio/
├── vitruvio.py        # punto de entrada del instalador
├── config.py          # declaración de opciones de configuración
├── contract.py        # contrato de entregas (manifiesto, firmas)
├── layout.py          # maquetas de salida por terminal
├── localization.py    # i18n (es|en)
├── view.py            # renderizado de paneles CLI
├── __init__.py
├── __main__.py
├── manifiesto.json    # manifiesto de la entrega r13
├── README.md
├── .gitignore
└── resources/
    └── i18n/
        ├── en.json
        └── es.json
```

---

## Uso rápido

```bash
# Instalar la entrega
python vitruvio.py instalar

# O en Windows
py vitruvio.py instalar
```

---

## Documentación

La carpeta `docs/` contiene las actas de debate, propuestas, contratos y checklist del desarrollo:

- `00_ANALISIS.md` — Análisis inicial
- `01_PROPUESTA.md` — Propuesta de diseño
- `04_CONTRATOS.md` — Contratos de interfaz
- `05_PRUEBAS_Y_DEPURACION.md` — Pruebas y depuración
- `06_NOTA_DE_VERSION.md` — Notas de versión
- `11_CONTRATO_INSTALADOR.md` — Contrato del instalador
- `24_DEUDA_TECNICA.md` — Deuda técnica conocida

---

## Principios

- **D-84:** Nunca guardar contraseñas.
- **D-91:** Todo por terminal, nada de GUI.
- Comandos, parámetros y flags **siempre en inglés**.
- Solo mensajes de UI localizables (español | inglés).
- Config portable junto a la aplicación (nunca en `~/.config/`).

---

## Versiones

- **Vitruvio 1.0.0-r13** — baseline oficial (estándar).

---

*Todo por terminal, nada de GUI.*
