# Primera prueba con Astro One4All 0.3

## Actualizar la microSD ya grabada

No hace falta formatearla. Conserva la Live 0.2 y sus aproximadamente 16 GiB de persistencia.

1. En Windows copia `dist/AstroOne4All-0.3-actualizar` al área visible de la microSD del sistema; no uses la SD de 128 GB de la Canon.
2. Expulsa la tarjeta. Arranca la Acer con lector/hub y cargador conectados; F12 permite elegir USB. Si el menú está desactivado y tu BIOS lo incorpora: F2 → Main → F12 Boot Menu → Enabled, F10. [Soporte Acer](https://community.acer.com/en/kb/articles/563-why-cant-i-get-the-f12-boot-menu-to-work-on-my-notebook-or-netbook).
3. En Equipo y sistema comprueba persistencia. F11 sale de pantalla completa. Termina tareas y cierra Astro One4All y PHD2.
4. Abre la carpeta de actualización desde el administrador de archivos. En una terminal dentro de ella ejecuta **`bash actualizar.sh`**. No necesita internet; comprueba hashes antes de instalar.
5. Abre Astro One4All desde el menú. Debe indicar **Prueba Live 0.3** y mostrar Atlas, Montura, Autoguiado y Enfoque.

La aplicación anterior sigue en `/opt/astroall`; la nueva, en `/opt/astroall-releases/0.3.0`. Conserva preferencias. `system/rollback-update.sh` restaura el lanzador anterior sin borrar esos datos. No hay conexiones, fotos ni movimientos automáticos al arrancar.

## Sin equipos

Prueba F8 y busca M31, Orión y Vía Láctea en Atlas. Cambia focal de 50 a 250 mm y comprueba el encuadre. Guarda un favorito y verifica que se conserva al reiniciar. En Ubicación introduce coordenadas reales, elevación y zona `America/Mexico_City`; comprueba fecha/hora del PC antes de confirmar el reloj.

Shift despierta la pantalla si se oscurece por ahorro de energía. El bloqueo automático está desactivado. El rojo global requiere comprobar la compatibilidad gráfica de la Acer.

## OAT en reposo

Conecta Arduino por USB. En Montura selecciona el perfil propio, puerto detectado y **19200**. Conectar consulta `:GVP#` y `:GVN#` en la misma conexión; debe mostrar la versión instalada, no la inferida del HEX.

El USB del Mega puede provocar auto-reset: conecta antes de iniciar una sesión. El perfil propio admite la familia 1.13.x; ante otra versión se detiene para revisar el controlador adecuado. Conserva las respuestas para diagnóstico. No modifica firmware, EEPROM, microstepping, calibración, límites o referencias.

Con espacio libre, prueba un movimiento breve a velocidad fina y suelta: debe detenerse. Después prueba seguimiento y PARAR. Home usa la referencia existente; no hay sensores ni AutoPA. El LCD 1602 debe conservar su funcionamiento autónomo.

## Canon: una sola foto corta

1. R50 con su SD de 128 GB, batería, cable de datos, M, RAW + JPG Med y enfoque manual. Cierra otros programas que la controlen.
2. Detecta la cámara en Equipo y sistema; vuelve a Sesión de fotos.
3. Exposición **1 s**, cantidad **1**, ISO Cámara o un ISO ofrecido por la cámara. Guiado desactivado; dither y centrado en 0.
4. Inicia el plan. Verifica físicamente CR3 y JPG en la SD; en la caché del PC debe descargarse solo el JPG y abrir la previsualización.
5. Prueba 3 fotos, luego 30 s. Cuando funcione, prueba 60 s Bulb y Detener: debe cerrar el obturador y marcar la toma interrumpida. Si no se confirma cerrar Bulb, revisa la cámara directamente antes de continuar.

Un error USB no demuestra que no exista la foto. Revisa la tarjeta antes de repetir. La toma incierta queda en `~/.local/state/astroall/session.json` y no se reanuda automáticamente.

## Resolver, centrar y guiar

Empieza a 50 o 55 mm con buen enfoque. Elige objetivo y focal real en Atlas; Al plan. Resolver comprueba el JPG. Centrar toma fotos de prueba de 2 s, corrige hasta 2° y verifica; si está más lejos, realiza primero un GoTo o ajusta manualmente. El 10 mm puede necesitar índices/parámetros adicionales por campo y distorsión; se incluyen índices 2MASS 4208–4219.

La Acteck aún necesita detección y estrellas en Linux. Añadir cámara USB prepara INDI/V4L2. En PHD2 selecciona INDI Camera y el equipo correcto en localhost:7624; para montura, INDI Mount en el mismo servidor. **No abras el puerto del Arduino desde PHD2.** Configura focal y tamaño de píxel reales, activa el servidor PHD2 y calibra/guía. El dither espera estabilización confirmada. Sin escala real, la gráfica usa píxeles.

Sin cámara guía, Centrar cada corrige el encuadre entre fotos; no elimina estelas durante una exposición. Los simuladores se seleccionan explícitamente y no validan dispositivos físicos.
