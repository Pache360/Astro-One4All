# Fuentes oficiales consultadas

Consulta: 2 de noviembre de 2026. La compatibilidad publicada no sustituye pruebas con los dispositivos concretos.

- [Requisitos NINA](https://nighttime-imaging.eu/docs/master/site/requirements/): Windows de 64 bits y al menos 3 GB de RAM.
- [Cámaras soportadas por libgphoto2](https://gphoto.sourceforge.io/proj/libgphoto2/support.php): R50 con captura, trigger, configuración y live view en la biblioteca actual.
- [Historial libgphoto2](https://github.com/gphoto/libgphoto2/blob/master/NEWS): el identificador R50 se añadió en 2.5.32.
- [libgphoto2 en Debian trixie](https://packages.debian.org/trixie/libgphoto2-6t64): versión 2.5.31; motivo para incorporar biblioteca posterior.
- [Publicación libgphoto2 2.5.33](https://github.com/gphoto/libgphoto2/releases/tag/v2.5.33): archivo oficial y digest obtenido de los metadatos del asset de GitHub.
- [Python-gphoto2](https://github.com/jim-easterbrook/python-gphoto2): API de cámara, metadatos, descarga y eventos.
- [Controlador INDI OpenAstroTech](https://drivers.indilib.org/mounts/open-astro-tech/lx200/lx200/): funciones y ejecutable del controlador específico.
- [Historial OAT](https://github.com/OpenAstroTech/OpenAstroTracker/releases?after=V1.8.53): compatibilidad INDI LX200 documentada por el proyecto.
- [Protocolo INDI](https://docs.indilib.org/protocol/) y [propiedades estándar](https://docs.indilib.org/drivers/standard-properties/): conexión, puerto, coordenadas de fecha y aborto.
- [Controlador INDI DSLR](https://drivers.indilib.org/cameras/generic/dslr-cameras/dslr-cameras/): diferencia entre almacenamiento local del controlador y SD de cámara.
- [Astrometry.net](https://astrometry.net/doc/readme.html): solver local e índices según escala angular.
- [Astropy IERS sin red](https://docs.astropy.org/en/stable/utils/iers.html): datos de orientación terrestre y configuración offline.
- [Astropy LeapSeconds](https://docs.astropy.org/en/stable/api/astropy.utils.iers.LeapSeconds.html): comparación de tablas y fecha de vigencia de segundos intercalares.
- [Persistencia Debian Live](https://live-team.pages.debian.net/live-manual/html/live-manual/customizing-run-time-behaviours.en.html): volumen persistente y `persistence.conf`.
- [Menú F12 de Acer](https://community.acer.com/en/kb/articles/563-why-cant-i-get-the-f12-boot-menu-to-work-on-my-notebook-or-netbook): acceso al menú y activación de esa opción desde F2 cuando el modelo la incorpora.
- [Alineación Ekos](https://kstars-docs.kde.org/en/user_manual/ekos-align.html): referencia funcional para contrastar el asistente propio.
- [API PHD2](https://github.com/OpenPHDGuiding/phd2/wiki/EventMonitoring): integración JSON-RPC, eventos, pulsos/dither y espera SettleDone implementados en 0.3.
- [OAT Control oficial](https://github.com/OpenAstroTech/OpenAstroTracker-Desktop): referencia de interfaz y comunicación serie; no se instala WPF/ASCOM en Linux.
- [Firmware OAT 1.13.22](https://github.com/OpenAstroTech/OpenAstroTracker-Firmware/tree/cbc0bca9a89966a18e149f145c0184a3d53865d3): referencia fijada para los comandos del controlador propio, tipos de respuesta y estado calculado. No acredita la versión instalada en el Arduino.
- [OpenNGC](https://github.com/mattiaverga/OpenNGC) y [HYG](https://github.com/astronexus/HYG-Database): catálogo/estrellas, CC BY-SA 4.0; revisiones y hashes en astroall/data/catalog-sources.json.
- [NASA M102](https://science.nasa.gov/mission/hubble/science/explore-the-night-sky/hubble-messier-catalog/messier-102/): identificación tradicional con NGC5866, indicada como tal en el catálogo.
- [Astropy TETE](https://docs.astropy.org/en/stable/api/astropy.coordinates.TETE.html): conversión explícita de ICRS a coordenadas aparentes de fecha, con ubicación y tiempo válidos.
- [PHD2 2.6.13](https://github.com/OpenPHDGuiding/phd2/tree/v2.6.13): fuente estable, compilación OPENSOURCE_ONLY sin SDK propietarios. SHA-256 del archivo fuente: 619993ce5a8baf1c62ba5dcb3ae485b4b82e0d8ce247d6b565b1db6a7de274cf.
- [Servidor INDI y FIFO](https://docs.indilib.org/indiserver/): incorporación de cámara guía al servidor compartido sin abrir otro puerto serie de montura.
- [pySerial API](https://pyserial.readthedocs.io/en/stable/pyserial_api.html): gestión de DTR/RTS; el kernel/controlador puede activar líneas al abrir el puerto. La aplicación no promete eliminar un reinicio de hardware sin prueba física.
- [Captura Ekos](https://kstars-docs.kde.org/en/user_manual/ekos-capture.html): un cálculo de exposición medido requiere características del sensor y del fondo del cielo. Las propuestas del atlas son heurísticas editables.
- [Placas del firmware OAT](https://github.com/OpenAstroTech/OpenAstroTracker-Firmware/blob/develop/Configuration.hpp): variantes de hardware; el perfil de la aplicación no configura sus pines. [Sucesor OpenAstroFirmware 2.x](https://github.com/OpenAstroTech/OpenAstroFirmware): una familia de firmware nueva requiere validación propia, no se infiere por el tipo de placa.
