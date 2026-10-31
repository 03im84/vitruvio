# Vitruvio — Guía de Instalación

---

## Requisitos

- Python 3.10 o superior
- No se requieren dependencias externas

---

## Instalar Vitruvio

Vitruvio es portable. Solo descarga o clona el repositorio:

```bash
git clone https://github.com/03im84/vitruvio.git
cd vitruvio
```

No hay paso de instalación adicional. Ejecuta directamente:

```bash
python vitruvio.py --help
```

En Windows:

```powershell
py vitruvio.py --help
```

---

## Instalar un paquete con Vitruvio

Una vez tengas Vitruvio listo, puedes instalar cualquier paquete de entrega:

```bash
python vitruvio.py install paquete.zip --destiny ./mi-app
```

---

## Desinstalar Vitruvio

Como Vitruvio no instala nada en el sistema, para "desinstalarlo" basta con borrar la carpeta donde lo clonaste.
