# Corrección Canon R50 · Astro One4All 0.3.1

Esta versión conserva un fallo de memoria al leer opciones del controlador. Para nuevas pruebas usa [0.3.2](CANON_R50_032.md); este documento queda como registro de la entrega anterior.

Esta actualización conserva las versiones anteriores, la persistencia y tus preferencias. No requiere internet ni volver a grabar la USB.

## Instalar en la Acer

1. Arranca la Live con persistencia. Termina las capturas y cierra Astro One4All y PHD2.
2. En el explorador pulsa Ctrl+L, escribe `/run/live/medium/AstroOne4All-0.3.1-actualizar` y pulsa Enter.
3. Abre **Actualizar Astro One4All.desktop** (puede mostrarse como **Actualizar Astro One4All a 0.3.1**).
4. Espera a que termine. Vuelve a abrir Astro One4All desde el menú y comprueba **0.3.1** en la barra lateral.

Si el explorador no permite ejecutar el acceso, pulsa Alt+F2 y escribe:

`xterm -e bash /run/live/medium/AstroOne4All-0.3.1-actualizar/actualizar.sh`

## Primera prueba de la cámara

Conecta la R50 por USB, con tarjeta y batería suficiente. Selecciona fotografía en **M**, **RAW + JPG Med**, enfoque **MF** y disparo **único** (sin temporizador). Para un objetivo manual sin contactos, habilita en la cámara el disparo sin objetivo si corresponde.

En **Equipo y sistema**:

1. Pulsa **Detectar Canon R50**. Esto consulta ajustes y libera la conexión.
2. Pulsa **Prueba foto · 1 s** y confirma. Comprueba una pareja CR3 + JPG nueva en la SD de la cámara.
3. Pulsa **Prueba Bulb · 3 s** y confirma. El programa selecciona Bulb, mantiene la orden de pulsación y envía soltar al terminar. Comprueba en la cámara la duración y el archivo.
4. Si ambas pruebas funcionan, usa **Sesión de fotos**: una toma de **60 s** para comprobar una exposición larga, y después el plan que necesites. Más de 30 s selecciona Bulb automáticamente.

Si utilizas **Detener captura / cerrar Bulb**, la toma interrumpida no se cuenta como completa. Si la cámara hace reducción de ruido de larga exposición puede tardar otro intervalo en escribir la foto; el programa espera sin repetirla.

## Si falla

Ahora aparece el error completo en una ventana y en **Actividad**, y se conserva la fase donde ocurrió. Pulsa **Equipo y sistema → Guardar diagnóstico**, incluso si no ejecutaste antes Comprobar equipo. El informe incluye versión, ajustes anunciados, órdenes Bulb elegidas y último error. No incluye imágenes ni el número de serie de la cámara.

El último informe también queda en `~/.local/state/astroall/camera-diagnostic.json`. No se vuelve a disparar automáticamente tras un fallo; revisa la SD antes de repetir.

## Correcciones y alcance

- La versión 0.3 buscaba `PressFull` / `ReleaseFull`; la libgphoto2 2.5.33 incluida publica **`Press Full` / `Release Full`**. Se seleccionan y envían ahora los nombres reales. También se reconoce el par posterior `Press Full MF` / `Release`.
- La orden para soltar queda preparada antes de abrir Bulb y se envía desde `finally`, sin consultar toda la configuración con el obturador abierto. Se procesan eventos en la misma conexión durante la exposición.
- La tarea de cámara usa los nombres del controlador en inglés aunque el escritorio esté en español. La interfaz sigue en español.
- Se comprueban modo y destino SD antes de cambiar exposición/ISO. Los CR3 permanecen en la cámara; solo se descarga el JPG correspondiente, con límite de tamaño y caché.
- Las pruebas automáticas y el laboratorio Linux comprueban la lógica y la instalación. La prueba con tu R50 física debe confirmar el funcionamiento real; que sea detectada no demuestra que haya disparado.

Fuentes: [controlador libgphoto2 2.5.33](https://github.com/gphoto/libgphoto2/blob/v2.5.33/camlibs/ptp2/config.c), [manual Bulb de Canon R50](https://cam.start.canon/en/C011/manual/html/UG-03_CustomShooting_0060.html).
