# Validación 0.3

Desarrollo: 3 de noviembre de 2026. Registros de esta versión: `dist/qa03-*`; las evidencias de 0.2 se conservan separadas.

Implementado: atlas/favoritos, encuadre/mosaico geométrico, planificación, controlador propio OAT/INDI, mando con vencimiento, secuencias con exposición/ISO, Bulb, centrado con JPG, cliente PHD2/dither, HFR y actualización offline.

Las pruebas cubren catálogo, J2000/fecha, cruce AR 0/polo, mosaicos, ubicación/reloj, Bulb cancelado y fallo de cierre, RAW/JPG, captura sin repetición, toma incierta, HFR de estrellas sintéticas y estabilización PHD2. Los recuentos finales corresponden a los registros de entrega.

Se probó un **servidor INDI real** con nuestro controlador y firmware emulado por puerto PTY Linux: identidad a 19200/8N1, distintos tipos de respuesta, GoTo con DEC −00:30:00, expiración del mando, pulsos, aborto y dos clientes compartiendo conexión. Sin Arduino ni comandos de calibración.

`dist/preview03` contiene pantallas renderizadas en Linux. Los ensayos de arranque/actualización se registran en `qa03-*` al completarse; una captura de interfaz aislada no acredita arranque Live.

## Resultados de la entrega

- **55 pruebas Linux aprobadas**; en Windows 54 aprobadas y una omitida porque comprueba enlaces de instalación propios de Linux.
- Servidor INDI real + nuestro controlador + OAT emulado por PTY: aprobado.
- PHD2 2.6.13 real + cámara simulada y salida On-camera simulada: calibración, guiado y dither con `SettleDone Status=0`.
- ISO 0.3 de 1.448.542.208 bytes: BIOS y UEFI amd64, USB2, 2 GB, sin red, aplicación automática. Memoria disponible en reposo: **1642 MiB BIOS / 1635 MiB UEFI**. Favorito guardado en BIOS conservado al apagar y arrancar UEFI.
- Actualización sobre Live 0.2, sin red: **248 archivos instalados verificados** como usuario normal, catálogo operativo y PHD2 2.6.13. Aplicación anterior y preferencia de prueba conservadas después del reinicio UEFI. Memoria disponible tras esa comprobación: **1627 MiB**.
- Lanzador de actualización: entrada de escritorio probada con GIO, xterm y un script inofensivo; la instalación real se probó por separado.
- SHA-256 ISO: `662e65789a7f750010c65ede29572fde790f6c796c293ac39a5324fe8ef0e727`.
- SHA-256 archivo de actualización: `398d00ad461af8cf4650ec23bce29598e5508f5aff6583567315d2c643890fcf`.

La actualización se copió y verificó en la microSD física, unidad F: `ASTROALL_02`, Generic STORAGE DEVICE de 31.266.439.168 bytes. Se conservaron la Live 0.2 y las particiones. Registro: `dist/qa03-physical-update.json`. Queda ejecutar el actualizador desde Linux; no se presenta la tarjeta como ya actualizada ni como probada físicamente en la Acer. No se formateó ningún dispositivo durante el desarrollo 0.3.

## Pruebas físicas pendientes

- Acer: arranque, Wi-Fi, USB/hub, rojo global y RAM bajo carga.
- OAT: versión instalada, límites, recorrido, Home, mando, seguimiento y pulsos.
- R50: par en SD, descarga exclusiva JPG, ISO, exposición y Bulb.
- Fotos de cada lente, centrado y polar en cielo real; mosaicos con orientación física.
- Acteck en Linux, telescopio guía, estrellas y calibración PHD2.

No hay meridian flip automatizado ni recorrido mecánico ilimitado. Comprueba recorrido y límites antes de una secuencia larga. No se asumen encoders, sensores Home, AutoPA o enfocador motorizado.
