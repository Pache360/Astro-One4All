# Validación de Astro One4All 0.2

Registro iniciado el 2 de noviembre de 2026, zona America/Mexico_City. Las comprobaciones de arranque posteriores a la construcción se entregan junto a la ISO en `dist/release.json` y `dist/arranque-live.png`; la copia de este documento dentro de la imagen se prepara antes de esas comprobaciones.

## Aplicación en Windows

- Python 3.12.14 en el equipo de desarrollo, no en la Acer.
- **30 pruebas automáticas aprobadas**. Incluyen selección explícita de tarjeta, confirmación RAW/JPG, rechazo de descargas grandes, caché limitada, respuesta del solver, mensajes INDI fragmentados, árbol XML acotado, rechazo de BLOBs, geometría polar norte/sur, tema rojo, previsualización, óptica, identidad OAT y UTC/local.
- Revisión visual de la interfaz propia y comprobación de sus cuatro páginas. No conecta dispositivos al abrirse.
- El entorno restringido de Windows necesitó una carpeta temporal escribible y sin espacios para las pruebas del solver; no es un resultado sobre rendimiento de Linux.

## Verificación que exige la construcción Linux

El ensamblado se detiene ante un error en cualquiera de estas comprobaciones. Los resultados exactos de la compilación entregada están en `/opt/astroall/qa-unit.log`, `/opt/astroall/qa-integration.json` y en los archivos homónimos de `dist`.

- Pruebas Python con pantalla X11 virtual.
- La Canon EOS R50 debe aparecer tanto en gphoto2 como en la biblioteca Python, utilizando libgphoto2 2.5.33. Esto comprueba el controlador instalado, no una cámara conectada.
- Conexión, solicitud GoTo y parada mediante un servidor INDI real con **Telescope Simulator**, sin motores.
- Hora sidérea y HA sin Internet con la tabla IERS incluida.
- El registro de integración indica si se ejecutó la resolución de una imagen de prueba. El archivo fotográfico privado de validación no se distribuye en la ISO.

## Imagen Live comprobada

El 3 de noviembre de 2026 se verificó la ISO final de 1.165.557.760 bytes. Su SHA-256 está en `dist/SHA256SUMS`; cada registro de arranque contiene ese mismo hash para identificar la imagen probada.

- **30 pruebas Linux aprobadas** y 16 archivos Python del sistema comprobados contra el código del proyecto.
- Conexión, solicitud GoTo y parada con servidor INDI real y Telescope Simulator.
- Plate solving de una imagen de prueba sin red y cálculo polar sintético con transformación completa Astropy en tres instantes.
- Arranque automático sin enviar teclas, desde USB 2.0 emulado, con **2048 MiB de RAM** y sin disco de sistema instalado.
- BIOS: panel iniciado, 1973 MiB de memoria total visible y **1624 MiB disponibles** en reposo.
- UEFI amd64, Secure Boot desactivado: panel iniciado, 1967 MiB de memoria total visible y **1619 MiB disponibles** en reposo.
- Persistencia virtual ext4 de 256 MiB: archivo guardado y sincronizado en BIOS, apagado del sistema y lectura correcta en el siguiente arranque UEFI. No es una medición de la tarjeta física de 32 GB.
- F8 activó y restauró el tema rojo en la sesión Live; capturas reales en `dist/arranque-live.png` y `dist/modo-noche-live.png`. La gamma global del panel de la Acer sigue pendiente de prueba.
- Bloqueador de sesión automático desactivado y comprobado como proceso ausente en ambas sesiones.

Registros: `dist/qa-boot.json`, `dist/qa-boot-uefi.json`, `dist/qa-persistence.json`, `dist/qa-integration.json` y `dist/release.json`. El consumo durante capturas y plate solving reales todavía debe medirse en la Acer.

## Tarjeta física grabada

El 3 de noviembre se grabó con Rufus la microSD autorizada, Generic STORAGE DEVICE, disco 3 de 31.266.439.168 bytes. La comprobación posterior fue de solo lectura:

- MBR, partición FAT32 `ASTROALL_02` accesible como F: y partición Linux tipo 0x83 de 17.179.900.416 bytes (aproximadamente 16 GiB).
- SHA-256 correcto de los seis archivos seleccionados: sistema comprimido, arranque EFI, núcleo e initrd, incluyendo sus nombres alternativos. Se compararon contra el manifiesto de la ISO probada.
- Las dos configuraciones de arranque copiadas contienen el parámetro `persistence`.

Registro: `dist/qa-physical-media.json`. Windows no montó la partición ext4: su contenido y la conservación de preferencias se deben comprobar al arrancar la Acer. La grabación verificada no acredita todavía funcionamiento de Canon, Arduino o Wi-Fi.

## Equipo real pendiente

No se ha comprobado físicamente esta entrega en la Acer, la Canon ni el Arduino. Permanecen pendientes:

- BIOS/UEFI real, Secure Boot, pantalla, Wi-Fi, alimentación del hub, estabilidad y velocidad por USB 2.0.
- Persistencia después de reiniciar en la microSD física.
- Descarga real de JPG y conservación física del par RAW/JPG en la SD de la R50.
- Respuestas reales GVP/GVN, GoTo, parada y convivencia con el mando LCD.
- Gamma roja global en la pantalla de la Acer y consumo durante una sesión real.
- Precisión polar bajo cielo real, GPS y cámara guía.

Bulb, guiado continuo y recentrado automático todavía no están implementados. Una simulación o una lista de cámaras compatibles no acredita funcionamiento físico.

## Aviso de tiempo observado durante el ensamblado

Se detectó que la tabla incluida por Astropy 7 caducaba en junio de 2025. Se compararon todas sus entradas con el archivo del sistema, vigente hasta junio de 2027: son idénticas, con última entrada enero de 2017 y TAI−UTC de 37 s. La imagen corregida configura Astropy para usar ese archivo vigente del sistema. Las pruebas de integración se repitieron y pasaron sin el aviso. El resultado se conserva en `dist/qa-time-tables.json`.

El primer arranque también detectó que faltaba `user-setup`: las pruebas de ventanas pasaban, pero no se creaba el usuario Live. Se añadió la dependencia a la receta y al sistema, se repitieron las pruebas Linux y se regeneró la ISO. El arranque de esa imagen corregida se registra por separado en `dist/qa-boot.json`.
