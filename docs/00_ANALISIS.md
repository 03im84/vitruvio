# 00 · ANÁLISIS DEL PROBLEMA Y SU CONTEXTO
**Proyecto:** Servidor FTP con CLI fácil e intuitiva
**Fase:** 1/8 — Análisis (no hay implementación)
**Fecha:** 2026-10-21
**Estado:** Borrador para debate

---

## 1. El problema real (no el aparente)

El pedido literal es "un servidor FTP, CLI, fácil, intuitivo". El problema de fondo, sin embargo,
no es *hablar FTP*: hablar FTP es un ejercicio de ~40 comandos de texto bien documentados desde
1985 (RFC 959). El problema real es que **los servidores FTP existentes fallan en el eslabón
humano**, y ahí es donde se pierden los datos y la paciencia:

| Dolor observado | Causa raíz | Consecuencia para el usuario |
|---|---|---|
| "Conecta pero `ls` se queda colgado" | Modo pasivo sin rango de puertos fijo / NAT anuncia IP privada | Sesión muerta sin ningún error visible. Es **el fallo nº1 de FTP** |
| "Tengo que editar `vsftpd.conf` a ciegas" | Configuración por fichero plano sin validación ni valores por defecto sanos | Prueba y error, servicio caído, frustración |
| "Puse mi carpeta y resulta que expuse todo el disco" | Falta de jaula (chroot) real, symlinks no resueltos | **Fuga de datos** |
| "Necesita root para el puerto 21" | Puerto privilegiado por defecto | El usuario corre todo como root → superficie de ataque enorme |
| "Mandé la contraseña en claro por el wifi del café" | FTP es texto plano por diseño | **Credenciales robadas** |
| "Error 530" | Mensajería de protocolo filtrada al humano | El usuario no sabe qué hacer |

> **Conclusión del análisis:** el valor diferencial no está en el protocolo (commodity), está en
> **configuración segura por defecto + diagnóstico preventivo + lenguaje humano**. Alineado con el
> lema *"el usuario puede fallar, el software no"*.

---

## 2. ¿Por qué FTP y no SFTP/HTTP? (validación del encargo)

Es obligatorio justificar la elección de protocolo antes de construir:

- **A favor de FTP:** es el único protocolo que hablan de forma nativa millones de dispositivos
  "mudos" — cámaras IP, escáneres multifunción, routers, PLC industriales, consolas retro, TVs,
  NAS antiguos, software CAD/contable legacy. Además, los exploradores de archivos de Windows,
  macOS (Cyberduck/Finder), GNOME y KDE montan FTP sin instalar nada.
- **En contra:** canal doble (control + datos) hostil a NAT/firewall; texto plano; sin integridad.
- **Mitigación estándar:** FTPS explícito (`AUTH TLS`, RFC 4217) sobre el mismo puerto de control,
  que mantiene la compatibilidad con clientes que no hablan TLS si así se configura.
- **Alternativas descartadas para este encargo:** SFTP (requiere stack SSH completo, imposible sin
  dependencias externas y fuera del pedido), HTTP (no lo hablan los dispositivos legacy).

**Veredicto:** FTP es la elección correcta *para el caso de uso de interoperabilidad*, siempre que
el diseño asuma que el protocolo es inseguro por naturaleza y compense en la capa de servidor.

---

## 3. Usuarios objetivo (3 perfiles) y lo que cada uno necesita

1. **El que comparte rápido** (doméstico/oficina): quiere "publicar esta carpeta en la red local,
   ya". Necesita: 1 comando, un QR/URL claro, apagarlo cuando termine. No debe tocar ni un JSON.
2. **El técnico de campo**: necesita *recibir* archivos de un aparato legacy que solo habla FTP.
   Necesita: control exacto del puerto, modo pasivo predecible, un log auditable de qué subió el
   aparato y cuándo.
3. **El equipo/docente**: varios usuarios con carpetas separadas, permisos distintos, cuota.
   Necesita: gestión de usuarios sin tocar ficheros a mano, y que nadie vea la carpeta del otro.

Los tres comparten una exigencia: **saber en todo momento si el servidor está bien o mal, y por qué.**

---

## 4. Restricciones técnicas verificadas en el entorno

| Hecho verificado | Implicación de diseño |
|---|---|
| `socket`, `socketserver`, `ssl`, `selectors`, `threading`, `hashlib`, `hmac`, `secrets`, `json`, `argparse`, `ftplib`, `zipfile`, `ipaddress`, `difflib`, `unittest` → **todos disponibles en la stdlib** | Un servidor FTP **completo con FTPS es 100 % viable sin dependencias externas** |
| `ftplib` está en la stdlib | Las **pruebas de ida y vuelta (soft tests) no necesitan ninguna librería**: el propio Python es el cliente de prueba |
| `openssl` está presente en el sistema | Podemos **autogenerar un certificado** para FTPS sin añadir `cryptography`. Si falta, degradamos con instrucciones claras |
| El sandbox corre **Python 3.13**, el objetivo es **3.10** | Se codifica contra el subconjunto 3.10 y se añade una **verificación automática de compatibilidad** (soft test que rechaza sintaxis >3.10). Punto a confirmar contigo |
| Puertos <1024 requieren root | **Puerto por defecto 2121**, nunca 21, salvo que el usuario lo pida explícitamente |
| El sandbox es un entorno aislado | Las pruebas de red se harán contra `127.0.0.1` con puertos efímeros, levantando y **dando de baja** el servidor en cada prueba |

---

## 5. Análisis de seguridad (modelo de amenazas resumido)

| Amenaza | Vector | Defensa que el diseño DEBE incluir |
|---|---|---|
| Fuga de todo el disco | `CWD ../../`, symlink que apunta fuera, rutas UNC/Windows | Jaula: resolver ruta real y verificar pertenencia al root; symlinks no seguidos por defecto |
| Robo de credenciales | Sniffing en red compartida | FTPS explícito (`AUTH TLS`); opción de *exigir* TLS antes de aceptar `PASS` |
| **FTP bounce** (usar el servidor como escáner de puertos ajeno) | Comando `PORT`/`EPRT` apuntando a una IP de terceros | Modo activo **desactivado por defecto**; si se activa, exigir que la IP coincida con la del canal de control y rechazar puertos <1024 |
| Secuestro de canal de datos | Un tercero se conecta al puerto pasivo antes que el cliente legítimo | Verificar que la IP que abre el canal de datos coincide con la del control; ventana de espera corta; puerto de un solo uso |
| Fuerza bruta de contraseñas | Reintentos automatizados | Límite de intentos + bloqueo temporal por IP + retardo progresivo + registro en auditoría |
| Agotamiento de recursos | Miles de conexiones ociosas | Tope global, tope por IP, timeout de inactividad, timeout de transferencia |
| Contraseñas en disco | Fichero de usuarios legible | PBKDF2-HMAC-SHA256 con sal por usuario; **jamás** texto plano; permisos 0600 en POSIX |
| Exposición accidental a Internet | Bind a `0.0.0.0` sin querer | Bind local por defecto + aviso explícito y legible al abrir a la red + detección de IP pública |
| Fuga de datos en los logs | Registrar el comando `PASS` | Redacción automática de credenciales en el logger |

---

## 6. Análisis del modelo de concurrencia (decisión de arquitectura)

| Opción | Pros | Contras | Veredicto |
|---|---|---|---|
| `asyncio` | 1 hilo, miles de conexiones | La E/S de ficheros **bloquea el bucle** → hace falta un executor igualmente; TLS asíncrono es delicado; depuración más difícil | Sobredimensionado |
| **Hilo por sesión + `selectors`** | E/S de ficheros natural y rápida; timeouts triviales; `ABOR` detectable con `select` durante la transferencia; código lineal y auditable | ~8 MB de pila por hilo → techo práctico de ~100 sesiones | **ELEGIDO** (con tope configurable, por defecto 20) |
| Proceso por sesión | Aislamiento máximo | Coste alto, complejo en Windows | Descartado |

Un servidor FTP personal/de equipo no verá 1000 conexiones simultáneas. *Austeridad de recursos,
máximos resultados*: el modelo de hilos acotados es el que da más seguridad y claridad por línea.

---

## 7. Inventario funcional del protocolo (alcance a debatir)

- **Núcleo RFC 959:** `USER PASS QUIT NOOP SYST TYPE MODE STRU PWD CWD CDUP LIST NLST RETR STOR
  APPE DELE RNFR RNTO MKD RMD ABOR STAT HELP ALLO SITE`
- **RFC 2428 (IPv6):** `EPSV EPRT` — necesario para redes modernas
- **RFC 3659:** `MLSD MLST SIZE MDTM REST` — listados fiables (los clientes modernos los prefieren) y **reanudación de descargas**
- **RFC 2389:** `FEAT OPTS` — negociación de capacidades y `OPTS UTF8 ON` (acentos y ñ en nombres de archivo)
- **RFC 4217 / 2228:** `AUTH TLS PBSZ PROT CCC` — FTPS explícito
- **Fuera de alcance propuesto:** FXP (transferencia servidor-a-servidor: es el vector del bounce
  attack), `SITE CHMOD` avanzado, compresión MODE Z, cuotas por grupo.

---

## 8. Riesgos del proyecto y mitigación

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Implementar FTP desde cero introduce un fallo de seguridad que una librería madura ya tiene resuelto | Media | Alto | Batería de soft tests ofensivos (escape de jaula, bounce, traversal, fuerza bruta) ejecutada en cada entrega; superficie reducida (sin FXP, sin modo activo por defecto) |
| Modo pasivo roto tras NAT en casa del usuario | Alta | Alto | **Diagnóstico activo**: el propio servidor se autoconecta al arrancar y avisa en lenguaje humano si el rango pasivo no es alcanzable |
| Divergencia 3.10 vs 3.13 del sandbox | Media | Medio | Soft test de compatibilidad sintáctica + prohibición explícita de APIs >3.10 en la guía de estilo |
| Crecimiento desordenado del código | Media | Medio | Contratos por módulo cerrados *antes* de escribir; fachada única `ServerFacade` |

---

## 9. Lo que el análisis concluye (entrada a la Propuesta)

1. Es viable y recomendable **cero dependencias externas**; la stdlib cubre el 100 % del alcance,
   incluido FTPS y las pruebas.
2. El diferencial del producto es la **capa humana**: asistente de arranque, diagnóstico de red
   preventivo, mensajes sin jerga, panel en vivo con tres temas.
3. La seguridad debe ser **por defecto**, no una opción: jaula, sin modo activo, sin anónimo,
   bind local, puerto no privilegiado, contraseñas derivadas.
4. El modelo de hilos acotados es suficiente y es el más auditable.
5. Hay **5 decisiones abiertas** que requieren tu criterio antes de ejecutar (ver `02_CHECKLIST.md`,
   sección D).
