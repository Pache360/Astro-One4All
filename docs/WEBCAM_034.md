# Astro One4All 0.3.4 — Webcam USB e imagen para PHD2

La microSD preparada instala la 0.3.4 en el siguiente arranque normal de la Acer.
Conserva los datos, la captura Canon y el controlador OAT. No requiere Internet.

## Primera conexión de la Acteck

1. Arranca y espera a que la aplicación muestre **0.3.4**. Conecta el OAT como
   antes: controlador propio, puerto del Mega, **19200 baudios**.
2. Cierra PHD2 si está abierto. En **Autoguiado**, pulsa **Buscar cámaras**.
   La integrada se oculta cuando Linux o su nombre permiten reconocerla.
3. Si no reconoces el nombre de la Acteck, pulsa **Identificar USB**. Sigue sus
   tres pasos: registrar cámaras conectadas, desconectar SOLO la webcam,
   detectar retirada, reconectar la misma webcam. No retires el hub ni la microSD.
   El programa seleccionará la cámara que desapareció y volvió a aparecer.
4. Pulsa **Conectar cámara** y luego **Ver imagen USB**. Verifica visualmente que
   corresponde a la Acteck. Recibe una sola imagen ligera y muestra su nombre.
5. Pulsa **Abrir PHD2**. Ahora prepara automáticamente un perfil propio con vídeo
   monocromo, cámara INDI y OAT como montura INDI. En PHD2 conecta el equipo.
   Se desactivan las opciones de óptica adaptativa, montura auxiliar y rotador
   en ese perfil; los demás perfiles se conservan.
6. Comprueba la imagen en bucle. Antes de calibrar con estrellas, revisa la focal
   y el tamaño de píxel REALES del equipo guía. Ver imagen no demuestra que la
   Acteck pueda guiar con estrellas. No se inventa el tamaño de su sensor.

Si el asistente no detecta cambios al desconectar la Acteck, Linux no ha visto
una cámara de captura desaparecer: comprueba el cable/puerto USB y alimentación.
Si una webcam externa tiene un nombre parecido al de la integrada, el asistente
puede identificarla sin depender del nombre ni del número video0/video2.

## Correcciones basadas en el registro «nuevo»

- El perfil guardado tenía abierta la Sunplus HD WebCam integrada.
- PHD2 tenía vídeo forzado desactivado, formato RGB, óptica adaptativa y ajustes
  de montura incompatibles. PHD2 requiere FITS de dos dimensiones o vídeo
  monocromo de un byte por píxel; el color provocaba error FITS o falta de frames.
- La aplicación confundía una orden manual rechazada con una pérdida de enlace;
  después intentaba cambiar el puerto de un controlador que seguía conectado.
  Ahora conserva la conexión, libera el mando y reutiliza el mismo enlace serie.
- El cambio de eje manual ya no se confunde con GoTo por una posición aún Busy.
  GoTo, Parking y Homing siguen bloqueando el movimiento manual hasta detenerlos.
- Los diagnósticos incluyen inventario, cámara identificada, conexión e imagen.

Para informar un fallo: **Equipo y sistema → Guardar diagnóstico**. Puede añadirse
« nuevo» al nombre. No hace falta borrar la tarjeta ni cargar otro firmware.

La captura Canon y la conexión OAT ya están confirmadas por los registros físicos.
El vídeo de la Acteck, su sensibilidad a estrellas y el guiado real requieren
comprobación física después de esta actualización. Las pruebas de webcam virtual
validan el recorrido Linux → V4L2 → INDI → imagen → PHD2, sin usar tu cámara.
