# Astro One4All 0.3.2 · captura y apagado

Esta actualización sustituye la aplicación activa, conserva las versiones anteriores y las preferencias, y no necesita internet ni formatear la microSD.

## Instalar

1. Arranca la Acer con persistencia. Termina las tareas y cierra Astro One4All y PHD2.
2. En el explorador pulsa Ctrl+L, escribe `/run/live/medium/AstroOne4All-0.3.2-actualizar` y pulsa Enter.
3. Abre **Actualizar Astro One4All.desktop**, que puede mostrarse como **Actualizar Astro One4All a 0.3.2**. Espera el mensaje de finalización.
4. Reinicia para recargar los accesos del escritorio. Si el menú sigue fallando antes de reiniciar: Alt+F2 → `sudo systemctl reboot`.
5. Comprueba **0.3.2** en la aplicación.

Alternativa para ejecutar el actualizador: Alt+F2 → `xterm -e bash /run/live/medium/AstroOne4All-0.3.2-actualizar/actualizar.sh`.

## Probar

La R50 debe estar en fotografía M, RAW+JPG, enfoque manual y disparo único. En **Equipo y sistema**, pulsa **Prueba foto · 1 s**; confirma una nueva pareja CR3+JPG en la tarjeta de la cámara. Después pulsa **Prueba Bulb · 3 s**. Si ambas funcionan, prueba una toma de 60 s en Sesión de fotos.

**Apagar o reiniciar** abre el diálogo del escritorio mediante su ruta completa. La aplicación pide terminar una tarea activa antes de abrirlo. Para apagar desde una terminal: `sudo systemctl poweroff`.

Si falla la captura, guarda el diagnóstico desde Equipo y sistema. Incluye la operación y la traza del error; no se repite la foto automáticamente.

## Qué se corrigió

Se leyó el registro de la microSD física: la R50 anunciaba M, cRAW+M, las exposiciones solicitadas y destino Memory card, pero fallaba durante configuring_exposure. El código recorría un iterador prestado por Python-gphoto2 después de liberar el objeto nativo que contenía las opciones. Ahora mantiene vivo ese objeto durante la lectura de exposición y de órdenes Bulb.

La reproducción usa Python-gphoto2 y libgphoto2 reales con una camlib virtual exclusiva del laboratorio: la expresión anterior devuelve memoria dañada o Bad parameters; la corregida conserva las opciones, configura 1 s / 2 s / Bulb y envía pulsar/soltar en una exposición simulada de 3 s. No prueba la mecánica ni el USB de la R50 física.

La lectura del sistema grabado confirmó que `/usr/bin/lxde-logout` y `/usr/bin/lxsession-logout` sí existían. La actualización cambia los accesos de salida a la ruta absoluta del diálogo y añade una opción dentro de la aplicación. No atribuye su fallo a un paquete inexistente.

La cámara física sigue pendiente de validar después de esta corrección. Las pruebas de software y del sistema Live se registran aparte en `dist/qa032-*`.
