# Validación de la corrección 0.3.1

La versión conserva el sistema base de la Live 0.2/0.3 y sus bibliotecas. La aplicación cambia a una carpeta `/opt/astroall-releases/0.3.1`; las versiones previas y la configuración del usuario se conservan. Las ISO originales no se reescribieron.

Se comprobaron 64 pruebas automáticas en Linux, incluidas las etiquetas reales `Press Full` / `Release Full`, soltar tras cancelación o error de pulsación/eventos, tiempo de exposición, rechazo de un archivo prematuro, RAW+JPG en SD, descarga exclusiva de JPG, caché limitada, exposición fija, error completo visible y diagnóstico guardable. Las comprobaciones previas de catálogo, montura, guiado, coordenadas, centrado y modo rojo también pasan. La cámara de estas pruebas es simulada.

El chequeo adicional crea widgets nativos con la biblioteca C libgphoto2 2.5.33 instalada, comprueba las funciones disponibles en Python-gphoto2 y extrae las opciones del código de ese controlador; comprueba tipos, valores y nombres. Python-gphoto2 no expone el constructor de widgets, por lo que el comprobador usa ctypes únicamente para crearlos. Esto no prueba una llamada real a Camera.set_single_config ni emula las operaciones USB/PTP de una R50.

Las evidencias de esta entrega quedan en `dist/qa031-linux.txt`, `dist/qa031-camera.json`, `dist/qa031-live.json` y `dist/qa031-live-reboot.json`. Los dos últimos comprueban instalación sin red, usuario normal, Live de 2 GB, lectura de los archivos por el usuario, preferencias y versiones previas conservadas, funcionamiento de PHD2 y permanencia después de reiniciar. `qa031-physical-copy.json` registra únicamente la copia a la microSD; no acredita la captura física.

Falta confirmar con la R50 del usuario: disparo de 1 s, Bulb de 3 s y 60 s, cancelación y pareja CR3+JPG en su SD. Un fallo USB real puede impedir enviar soltar; el programa lo informa y detiene el plan, sin repetir la exposición automáticamente. [Procedimiento](CANON_R50_031.md).
