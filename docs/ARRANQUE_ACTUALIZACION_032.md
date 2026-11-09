# Actualización 0.3.2 al arrancar

El registro leído de la microSD confirmó `application_version: 0.3.1` y `/opt/astroall-current → /opt/astroall-releases/0.3.1`. La carpeta 0.3.2 estaba copiada en FAT32, pero no instalada en la persistencia. El último intento falló al abrir USB con `[-1] Unspecified error`, antes de disparar; ese registro no contiene el motivo PTP detallado.

El mantenimiento añade a las entradas normales de BIOS y UEFI el parámetro:

`live-config.hooks=file:///run/live/medium/live/config-hooks/astroall-update-032.sh`

El paso se ejecuta antes del escritorio, verifica los hashes fijados del paquete y del instalador 0.3.2 ya probado, lo instala si no está activo y confirma la versión. Después instala un diagnóstico USB opcional. No hace fotos ni se conecta a la montura o a la cámara al arrancar. Conserva las versiones anteriores y los ajustes. En siguientes arranques reconoce la 0.3.2 activa y omite la reinstalación.

La versión de live-config incluida sigue usando la ruta antigua `/lib/live/mount/medium` al buscar configuración en el medio, mientras live-boot monta esta imagen en `/run/live/medium`. Por eso se utiliza el parámetro explícito con la ruta comprobada. La entrada de recuperación mantiene sus parámetros anteriores.

## Uso en la Acer

1. Expulsa la microSD de Windows y arranca la entrada normal de Astro One4All en la Acer.
2. Espera a que termine el arranque; la primera actualización puede añadir unos minutos. La aplicación debe mostrar **0.3.2** y **Equipo y sistema → Apagar o reiniciar**.
3. Apaga y vuelve a encender la Canon, con fotografía M, RAW+JPG y enfoque manual. Conéctala por USB y prueba **Foto · 1 s**; después **Bulb · 3 s**. Confirma los archivos CR3+JPG en la SD de la cámara.
4. Si sigue fallando al conectar: cierra Astro One4All, pulsa **Alt+F2**, escribe **`astroall-canon-diagnose`** y pulsa Enter. También está en el menú como **Diagnosticar Canon USB (sin disparar)**. El diagnóstico consulta conexión y ajustes; no toma fotos ni reinicia USB.

El informe USB queda en `~/.local/state/astroall/canon-usb-check.json`. El resultado del paso de arranque queda en `/var/lib/astroall/boot-update-032.status` y el detalle en `/var/log/astroall-boot-update-032.log`. Un fallo del actualizador abre una terminal con el registro al entrar al escritorio.

## Cambios reversibles del medio

Se añaden `live/config-hooks/astroall-update-032.sh` y `live/config-hooks/canon-usb-check.py`. Se modifican los archivos de texto `isolinux/live.cfg`, `boot/grub/grub.cfg` y sus sumas en `sha256sum.txt`; los tres originales se guardan con el sufijo `.before-auto032`. No se modifica la tabla de particiones ni el sector de arranque. Para desactivar el paso automático, restaura esos tres archivos originales. La aplicación instalada permanece en la persistencia.

Este paso está fijado a la versión 0.3.2. Desactívalo antes de instalar una versión posterior.

Las pruebas virtuales de arranque se registran aparte de la comprobación física de la R50. Que la actualización se instale no confirma una captura real. Los archivos originales de las versiones 0.3/0.3.1/0.3.2 permanecen intactos.

Referencia: [opción hooks de Debian Live](https://manpages.debian.org/trixie/live-config-doc/live-config.7.en.html).
