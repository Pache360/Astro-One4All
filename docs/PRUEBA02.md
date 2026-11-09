# Primera prueba Live 0.2

Objetivo de esta entrega: arrancar la Acer desde la microSD y probar detección del OAT, una captura corta con la R50 y vista del JPG. La ISO ya se construyó y pasó arranque BIOS/UEFI y persistencia en máquina virtual; los resultados están en `VALIDACION.md`. Falta la prueba física de Acer, Canon y montura.

## Tarjeta autorizada

El usuario autorizó borrar la microSD del sistema. En la inspección del 2 de noviembre de 2026 aparece como **disco 3, Generic STORAGE DEVICE, USB, 29.12 GiB**, con partición visible **F:**. Los números y letras pueden cambiar al desconectar: hay que volver a comprobar tamaño y tipo antes de grabar. La SD **128 GB de la Canon no es el destino**.

## Grabar desde Windows

La tarjeta de esta sesión ya quedó grabada y sus archivos se comprobaron contra la ISO; el registro es `dist/qa-physical-media.json`. Los pasos siguientes sirven para repetir la grabación en otra tarjeta.

La entrega está en `dist/Astro-One4All-0.2-prueba-amd64.iso`, acompañada de `SHA256SUMS`. **Preparar USB Live.cmd** comprueba la imagen y su prueba de arranque, y abre Rufus portátil oficial con la ISO seleccionada. Windows solicita permisos de administrador para grabar. La firma y el origen del grabador se documentan en `dist/media-writer/SOURCE.json`.

1. En Dispositivo, selecciona la microSD de aproximadamente 32 GB.
2. Selecciona la ISO de Astro One4All. Usa el modo ISO cuando Rufus lo ofrezca.
3. Configura **16 GB de persistencia** si Rufus muestra el control correspondiente. La persistencia permite conservar preferencias y guardar los JPG en la tarjeta, sin ocupar un sistema de archivos temporal en RAM.
4. Mantén el esquema compatible con el firmware de la Acer; se preparan BIOS y UEFI amd64. No está validado firmware UEFI de 32 bits.
5. Revisa de nuevo el dispositivo y pulsa Empezar. Esto borra la tarjeta elegida.

Si no aparece la opción de persistencia o el programa advierte incompatibilidad con el modo ISO, no improvises un formato distinto: debe revisarse ese resultado. No se considera lista la sesión de captura hasta comprobar la persistencia después de reiniciar.

## Arranque y comprobación

1. Conecta lector y hub al puerto funcional de la Acer, alimentada por su cargador.
2. Al encender la Acer, pulsa F12 para abrir el menú de arranque y elige la unidad USB. Si el menú está desactivado y existe esa opción en tu BIOS: entra con F2, Main → F12 Boot Menu → Enabled y guarda con F10. Son las indicaciones de [soporte oficial de Acer](https://community.acer.com/en/kb/articles/563-why-cant-i-get-the-f12-boot-menu-to-work-on-my-notebook-or-netbook); las opciones pueden variar entre modelos.
3. **Astro One4All (amd64)** se selecciona automáticamente tras 5 segundos; Enter lo inicia antes. El panel abre a pantalla completa al cargar Linux; **F11** cambia a ventana y **Esc** sale de pantalla completa.
4. En Equipo y sistema, ejecuta Comprobar equipo. Comprueba que reconoce persistencia y que anuncia Canon R50 en la biblioteca.
5. Prueba **F8**. La aplicación debe volverse roja; el rojo global de pantalla requiere compatibilidad X11 y se debe confirmar en la Acer.
6. Guarda una preferencia de zona horaria, reinicia y comprueba que sigue guardada.

El bloqueo automático está desactivado en esta imagen dedicada. El ahorro de pantalla puede oscurecer la imagen después de dejarla inactiva: pulsa Shift para volver al panel. Eso no detiene la sesión de captura.

## OAT: primero identidad en reposo

En Montura indica el puerto detectado y **19200 baudios**. Con el OAT en reposo y sin controlador INDI utilizando el puerto, consulta Identificar OAT. Deben registrarse las respuestas reales de `:GVP#` y `:GVN#`; el HEX preparado v1.13.22 no acredita la versión instalada.

Abrir el puerto USB de un Mega puede reiniciarlo por su circuito de auto-reset; por eso se hace antes de una sesión activa. No se modifica firmware, EEPROM, pasos ni límites.

Después prueba el controlador INDI, conexión y lectura de estado. GoTo y parada necesitan comprobarse físicamente dentro del recorrido libre. El control LCD autónomo debe mantenerse.

## Canon: una sola foto corta

1. Canon con SD **128 GB**, modo M, RAW + JPG Med, enfoque manual y exposición fija de **1 segundo**. No uses Bulb todavía.
2. Detecta la R50 desde Equipo y sistema y vuelve a Sesión de fotos.
3. Fotos: **1**. Pulsa Iniciar captura.
4. Confirma la vista del JPG en el panel. Comprueba en la SD que existen tanto CR3 como JPG.
5. Si es correcto, prueba 3 fotos y el botón de detener entre tomas. Después aumenta el tiempo fijo, hasta 30 s como máximo en esta versión.

Los doce índices 2MASS de escalas 08–19 están incluidos y se usaron para resolver una imagen de prueba sin Internet. Empieza con el 50 mm o el 55–250 a 55 mm; el ultrangular requiere evaluar distorsión y comportamiento del solver.

## Alcance

La interfaz es propia y funcional para estas pruebas. Todavía faltan Bulb, guiado continuo y recentrado automático entre capturas. El polar de tres puntos es experimental: no es AutoPA ni una función nueva del firmware. La validación en máquina virtual no demuestra que el hardware real funcione.
