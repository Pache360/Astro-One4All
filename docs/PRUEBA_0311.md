# Astro One4All 0.3.11 · imagen guía sin mosaicos

La microSD preparada aplica esta actualización al arrancar normalmente con
persistencia. Comprueba la versión **0.3.11**. Conserva perfiles, fotos, planes
y registros; no formatea ni modifica el firmware de la montura.

## El problema encontrado

El registro automático y la imagen guardada de la Acer muestran que la cámara
cambió a YUYV 640 × 480 mientras la vista guía seguía usando 1280 × 720.
Al interpretar ese fotograma con un tamaño incorrecto, aparecían copias de la
escena y franjas. Blanco y negro es normal para esta vista; esas repeticiones no.

INDI 1.9.9 puede renegociar el tamaño del dispositivo al cambiar el formato sin
actualizar todavía las dimensiones CCD y de streaming. La 0.3.10 omitía aplicar
la resolución si su casilla ya figuraba seleccionada. Ahora se aplica explícitamente
el tamaño, se vuelven a leer las dimensiones del controlador y se exige que
coincidan antes de iniciar vídeo. La imagen recibida también se contrasta con
el tamaño confirmado. Una discrepancia detiene la vista previa con el motivo.
Al conectar se reafirma también el modo monocromo para sincronizar el formato
de píxeles interno después de una transición desde RGB.

## Comprobación en la Acer

1. Cierra PHD2 si estaba abierto y entra en Autoguiado.
2. Busca cámaras, elige la Acteck USB y pulsa **Probar imagen USB**.
3. Debe aparecer una sola escena, sin mosaicos ni bandas, con **640 × 480**
   indicado debajo. El programa guarda una miniatura para no cargar la RAM.
4. Después abre PHD2 y conecta los equipos. La cámara guía sigue siendo opcional:
   OAT + R50 pueden fotografiar y comprobar encuadre por JPG sin ella.

Si reaparece el problema, la aplicación guarda automáticamente el formato,
dimensiones, estado INDI y última vista previa. Guardar diagnóstico añade esos
datos al informe exportado; no hace falta repetir muchas capturas.

## Qué se comprobó físicamente y qué falta

La Acteck USB 0c45:64ab entregó tres imágenes completas en Windows: JPEG
1280 × 720 a 30 fps, YUYV 640 × 480 a 30 fps y YUYV 1280 × 720 a 10 fps.
Las imágenes de habitación permanecen en el área privada de diagnóstico y no
se incluyen en la actualización ni en el archivo de código.

Las pruebas Linux usan el controlador INDI real, PHD2 y una webcam virtual.
Una simulación aislada hace que el dispositivo cambie de 1280 × 720 a 640 × 480
al seleccionar YUYV, reproduciendo la negociación observada. Ese componente de
prueba no se instala en la Live ni se aplica a dispositivos del usuario.

La confirmación final de imagen en la Acer y el enfoque/sensibilidad con estrellas
siguen pendientes. Una imagen diurna limpia no acredita todavía autoguiado.

Referencia del controlador utilizado:
https://github.com/indilib/indi/blob/v1.9.9/drivers/video/v4l2driver.cpp
