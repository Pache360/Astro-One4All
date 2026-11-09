# Astro One4All

Sistema propio y abierto de astrofotografía para recuperar portátiles antiguos. Primer equipo objetivo: Acer ES1-111 (2 GB RAM), Canon EOS R50 y OpenAstroTracker con Arduino Mega + RAMPS 1.4. Interfaz en español, Linux desde microSD de 32 GB por USB 2.0 y originales en la SD de la cámara. Licencia MIT para el código propio.

**Versión 0.2 · prueba Live experimental.** Interfaz propia renovada, vista del último JPG y flujo de prueba desde microSD. El estado de construcción y verificaciones se registra en [VALIDACION.md](docs/VALIDACION.md). No se ha validado físicamente la Acer, R50 o montura; las pruebas simuladas no confirman esa compatibilidad.

La ISO de prueba ya está en `dist`: **1,09 GiB**, con arranque automático BIOS y UEFI amd64 comprobados en una máquina virtual de 2 GB, sin red. El panel dejó **1624 MiB disponibles** en BIOS y **1619 MiB** en UEFI durante esas mediciones en reposo. La persistencia virtual conservó un archivo después de apagar y volver a arrancar. Son resultados del entorno virtual; falta medir la Acer con los dispositivos conectados.

Para la primera sesión sigue [PRUEBA_DE_HOY.md](docs/PRUEBA_DE_HOY.md). **Preparar USB Live.cmd** comprueba el resultado de arranque y el SHA-256 antes de abrir el grabador con la imagen seleccionada. La selección del dispositivo y la persistencia se revisan en el grabador.

## Lo que ya hay

- Aplicación de escritorio propia y ligera con diagnósticos, captura, óptica, control de montura y asistente polar. No depende de abrir Ekos para usar su interfaz.
- Modo noche rojo de la aplicación (F8) y ajuste global de pantalla en Linux/X11 mediante rampas de color, con restauración al salir; compatibilidad del controlador de pantalla por probar.
- Cliente INDI propio: descubre propiedades, configura puerto/baudios, conecta, envía GoTo de fecha y solicita parada. Pendiente de probar con el Arduino real.
- Consulta directa y exclusiva de identidad OAT: `:GVP#`/`:GVN#`, 19200/8N1 iniciales configurables y registro de respuestas. No deduce firmware instalado a partir del HEX preparado.
- Tiempo UTC y local, zona IANA persistente y editable al viajar. Hora sidérea/HA calculables con Astropy cuando se aportan longitud, reloj verificado y AR de fecha; el GPS no se lee automáticamente aún.
- Asistente polar propio experimental: captura/resuelve tres puntos mientras el usuario gira solo AR con el mando; transforma cada centro al horizonte en su instante y estima el ajuste físico de la base. No incluye aún refresco gráfico en vivo.
- Adaptador experimental R50: selecciona y comprueba destino tarjeta, exige RAW+JPEG, dispara con la exposición fija que tenga la cámara (hasta 30 s), confirma ambos nombres en DCIM y descarga exclusivamente el JPG correspondiente. Nunca solicita descargar ni borrar un RAW.
- Caché circular de JPG de 64 MiB en disco, con límite de 16 MiB por archivo. Un JPG necesita temporalmente memoria para transferirse y analizarse; no se promete consumo cero de RAM.
- Resolución astrométrica local de un JPG mediante astrometry.net, con límite de tiempo y campo angular aproximado. La receta 0.2 incorpora los índices 2MASS 4208–4219 para la prueba; otras escalas pueden requerir catálogos adicionales.
- Medición de deriva entre dos centros resueltos. **No envía correcciones a la montura ni sustituye el autoguiado.**
- Receta Debian 13 amd64 con LXDE, arranque a la app propia, INDI, controlador Canon, webcams y zram. Compila libgphoto2 2.5.33 porque la R50 se añadió después de la versión incluida por Debian. KStars/Ekos es opcional para comparación y diagnóstico, no el núcleo de la app.

## Diseño del sistema completo

| Necesidad | Componente / estado |
|---|---|
| Arrancar sin HDD | ISO Live: BIOS y UEFI amd64, USB 2.0 emulado, 2 GB, panel automático y persistencia virtual comprobados; Acer pendiente |
| Montura y GoTo | Cliente propio → INDI → firmware OAT; conexión, GoTo y parada con servidor INDI y Telescope Simulator; hardware pendiente |
| Secuencias | Secuenciador propio básico; usa exposición e ISO seleccionados en la cámara |
| Enfoque, planificación y catálogo | Pendientes |
| Asistente de alineación polar | Propio de tres puntos; geometría verificable, cielo real pendiente |
| Autoguiado con segunda cámara | Backend de guiado e integración pendientes; cámara por identificar |
| RAW+JPG en SD, solo JPG al ordenador | Adaptador experimental separado; pendiente de prueba con R50 |
| Recentrado periódico por JPG | Medición implementada; integración automática con captura/INDI pendiente |
| Bulb, exposiciones >30 s | Pendiente de verificar y desarrollar en el adaptador |
| Un solo flujo de trabajo automático | Pendiente de integrar ambos modos sin competir por la cámara |

INDI y libgphoto2 son controladores internos; la experiencia de uso se construye en Astro One4All. Si usas Ekos como auxiliar, desconecta su Canon antes de capturar desde nuestra app. «Local» de INDI significa disco del ordenador, no SD de cámara. El cliente INDI propio de montura rechaza imágenes BLOB para que ese enlace no reciba fotos grandes.

## Probar ahora sin dispositivos

En este equipo Windows puedes abrir **`Abrir vista previa.cmd`** para ver la interfaz. No conecta dispositivos al iniciar. Esta vista previa no es el sistema USB final.

Desde esta carpeta, con Python 3.10 o posterior:

```sh
python -m astroall demo
python -m astroall doctor
python -m unittest discover -s tests -v
python -m astroall panel
```

El panel necesita Tk. El control real de cámara necesita Linux, `python3-gphoto2` y una libgphoto2 que anuncie exactamente `Canon EOS R50`. Los comandos de simulación y pruebas no disparan fotos ni mueven motores.

## Preparar el sistema USB

Consulta [la guía de construcción](docs/USB.md). La receta se ejecuta en un **equipo de construcción Debian 13 amd64**, con Internet y espacio de disco. En este Windows se utiliza una máquina virtual QEMU portátil en `build/vm`, con Debian oficial, sin instalar WSL ni reiniciar Windows. No forma parte de lo que se ejecuta en la Acer.

Antes de grabar hay que identificar la tarjeta concreta. En esta sesión se autorizó borrar la microSD de 32 GB, identificada como Generic STORAGE DEVICE de 29,12 GiB; su número o letra pueden cambiar al desconectar. La SD de 128 GB de la Canon es independiente. El arranque, Wi-Fi, pantalla y persistencia se deben comprobar también en la Acer real.

## Primera prueba con la R50

1. Arranca Linux con persistencia funcionando. Cámara con SD, batería y cable USB de datos. Desconecta la Canon en Ekos y cierra otros programas que la utilicen.
2. Ajusta en la cámara modo M, enfoque manual, RAW + JPG Med y exposición fija corta (por ejemplo, 1 s). Desactiva apagado automático durante la prueba.
3. Ejecuta `python3 -m astroall camera-info` y revisa los valores detectados.
4. Ejecuta `python3 -m astroall capture --count 1`.
5. Comprueba físicamente en la SD que existen **RAW y JPG**, y en la caché del ordenador que solo se descargó un JPG. Verifica que la foto abre correctamente.
6. Solo después prueba series cortas y exposiciones de hasta 30 s. Si el par no se confirma o hay un error, el programa se detiene sin repetir la foto.

El adaptador modifica el destino de captura a tarjeta y lo deja así. No cambia formato, ISO ni tiempo: usa los que selecciones en la cámara. Los nombres de ajustes varían entre versiones; si no identifica un valor de forma explícita, se detiene.

Para resolver un JPG cuando ya estén los índices locales:

```sh
python3 -m astroall solve /ruta/IMG_0001.JPG --width-deg 6.4 --index-dir /home/astro/astroall-data/indexes
```

`6.4` es solo un ejemplo, no la configuración de tu lente. El ancho aproximado se calcula como `2 × atan(ancho_sensor_mm / (2 × focal_mm))`, convertido a grados. No debes sustituir la focal real por una «equivalente full-frame».

## Información que falta

El equipo completo está documentado en [EQUIPO.md](docs/EQUIPO.md): montura operativa, TMC2209 standalone 1/64, poleas 16T, LCD 1602, GPS Serial2/D17, control 19200/8N1. El HEX preparado v1.13.22 no confirma firmware instalado. Faltan las respuestas reales, puerto actual, recorrido disponible, cámara guía funcional y arranque en la Acer. La Canon tiene SD de 128 GB; la microSD del sistema es de 32 GB y trabaja por USB 2.0. Los cuatro lentes, incluido el TTArtisan 10 mm f/2, están confirmados.

El chat compartido solo proporcionó cinco intercambios recientes sobre la Nexxt; la configuración actual se tomó del contexto técnico que el usuario aportó después. No se sustituyen esos datos por los de otras monturas o computadoras.

Consulta [la puesta en marcha y las pruebas pendientes](docs/PUESTA_EN_MARCHA.md), [las decisiones técnicas](docs/DISENO.md) y [las fuentes oficiales](docs/FUENTES.md).

Consulta los [resultados de validación](docs/VALIDACION.md), distinguiendo la aplicación, la imagen virtual y el equipo real.
