# «Operation not supported» al abrir Dispositivos

La vista `computer:///` del explorador requiere GVfs. La selección mínima de paquetes de las primeras imágenes no lo incluía; esto se reprodujo mediante GIO como usuario normal en la Live virtual. El error no es una prueba de detección o fallo de la Canon ni del Arduino.

## Continuar con la actualización

En el explorador: Aceptar → Ctrl+L → escribe `/run/live/medium/AstroOne4All-0.3-actualizar` → Enter. Abre `Actualizar Astro One4All.desktop`. Esta carpeta se encuentra directamente en la microSD y no requiere la vista virtual Dispositivos.

Para conectar la Canon y el Arduino utiliza Equipo y sistema y Montura de Astro One4All. El explorador muestra principalmente almacenamiento, no equivale al administrador de dispositivos de Windows.

## Reparación offline

El paquete `dist/AstroOne4All-reparar-explorador` contiene GVfs, UDisks2 y las dependencias resueltas respecto de la Live original. No solicita gvfs-backends ni su backend de automontaje de cámaras. `system/packages.list` ya incluye la dependencia para las siguientes construcciones; las ISO entregadas anteriormente se conservan y requieren este parche.

Apaga la Acer antes de retirar la microSD. Conéctala a Windows y abre `Copiar reparación del explorador.cmd`. Copia y verifica solo la carpeta de reparación, sin formatear. Arranca la Live con persistencia, termina las capturas y abre esa carpeta mediante Ctrl+L y `/run/live/medium/AstroOne4All-reparar-explorador`. Ejecuta `Reparar explorador.desktop`, espera a que termine y reinicia Linux.

Alternativa desde una terminal dentro de la carpeta: `bash reparar-explorador.sh`. El instalador verifica SHA-256 y deshabilita los repositorios de red: utiliza los paquetes locales.

Prueba aprobada: la Live virtual de 2 GB reprodujo `Operation not supported` (GIO, código 15); tras instalar el paquete sin red, `computer:///` pudo enumerarse como usuario `astro`. Se comprobó también `sudo` del usuario Live y que no se añadió el backend de automontaje de cámaras. Registro: `dist/qa-explorer-repair.json`.

El reparador ya se copió y verificó en `F:\AstroOne4All-reparar-explorador` (59 archivos), sin formatear ni modificar particiones. Registro: `dist/qa-explorer-physical-copy.json`. Queda ejecutarlo desde la Live y reiniciar; no se presenta como ya instalado en la Acer.

Referencia: [GVfs en Debian](https://packages.debian.org/trixie/gvfs) y [componentes de gvfs-daemons](https://packages.debian.org/trixie/amd64/gvfs-daemons/filelist).
