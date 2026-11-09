# Astro One4All 0.3.3 — Cámara guía USB y conexión OAT

Esta actualización conserva la captura Canon de la 0.3.2. Se verificaron en los
registros físicos cinco fotos de 1 s completas, RAW/CR3 + JPG en la SD y solo JPG
transferido. Esto no acredita todavía una prueba física de Bulb prolongado.

La microSD preparada instala la 0.3.3 al arrancar normalmente en la Acer, sin
Internet ni formatear. Espera a que aparezca la aplicación y comprueba la versión.
Los perfiles, calibraciones del firmware, fotos y versiones anteriores se conservan.

## Montura

1. Conecta y alimenta el OAT. En Montura pulsa **Buscar puertos**.
2. Perfil `indi_astroall_oat`, puerto del Arduino (en tu prueba:
   `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0`), **19200** baudios.
3. Pulsa **Conectar**. Debe mostrar la versión real, estado, AR y DEC.
4. Mantén pulsado brevemente una dirección del mando y comprueba el movimiento;
   al soltar se detiene el movimiento manual. Elige una zona con recorrido libre.

El fallo corregido ocurría después de identificar producto y firmware: OAT
1.13.22 devuelve `+DD*MM'SS#` y el programa esperaba `+DD*MM:SS#`.
Se aceptan ambas respuestas, conservando el signo incluso para −00 grados.
También se corrigió el reconocimiento de las capacidades de imagen que INDI
anuncia al conectar una cámara: esa descripción ya no se confunde con una imagen
recibida por el cliente de montura. El servidor carga el controlador de montura
solicitado aunque ya estuviera en marcha con una cámara.
El programa no cambia Home, EEPROM, límites ni calibración de motores.
PHD2 utiliza la montura compartida por INDI; no debe abrir el Arduino directamente.

## Cámara guía Acteck / USB

1. En **Guiado** pulsa **Buscar cámaras**.
2. Elige la Acteck por nombre y conexión. También aparece la integrada de la
   laptop; no se selecciona una cámara automáticamente la primera vez.
3. Pulsa **Conectar cámara elegida**. El programa configura el puerto antes de
   abrirla, comprueba la respuesta y guarda su identidad. Si la USB falta, no
   la sustituye por la integrada. Se excluyen los puertos que solo entregan
   metadatos. Si no aparece la Acteck, comprueba cable, hub y alimentación.
4. Cierra PHD2 si estaba abierto. Puedes indicar focal y tamaño de píxel reales
   del equipo guía; no uses la focal de la Canon. Si no los conoces, deja los
   campos vacíos y revísalos en PHD2 antes de calibrar.
5. Pulsa **Preparar perfil PHD2** y luego **Abrir PHD2**. Se crea/elige un perfil
   «Astro One4All - USB + OAT», cámara **INDI Camera**, montura **INDI Mount**,
   servidor `localhost:7624`. No selecciones On-AO ni el puerto serie.
6. Conecta el equipo en PHD2 y comprueba que la imagen es de la cámara USB.
   Primero enfoca y prueba con estrellas; ver imagen no acredita poder guiar.

Para cambiar de cámara, desconéctala primero en PHD2. La aplicación no interrumpe
una cámara que está conectada a otro puerto. Los demás perfiles PHD2 se conservan;
se guarda una copia de su configuración antes de crear el perfil propio.

## Si falla

En **Equipo y sistema → Guardar diagnóstico** se incluyen ahora el perfil de
montura, cámara guía elegida y respuestas serie/error de la última conexión OAT.
No vuelvas a grabar la tarjeta ni cargues firmware para corregir este problema.

Comprobado mediante pruebas automatizadas y controladores reales en un Linux
aislado, con OAT emulado por puerto serie. La conexión de la Acteck y el control
físico de esta montura con la 0.3.3 requieren la siguiente prueba en la Acer.
