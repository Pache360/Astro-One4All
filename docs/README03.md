# Astro One4All

Observatorio portátil propio, en español, para recuperar computadoras antiguas. Linux Live desde USB, interfaz nativa ligera, modo rojo y originales en la SD de la Canon. Primer equipo objetivo: Acer ES1-111 con 2 GB de RAM, sin HDD, Canon EOS R50 y OpenAstroTracker Mega + RAMPS 1.4.

**0.3 · versión de prueba.** Atlas local y mando de montura propio, con actualización sin formatear la Live 0.2. Compatibilidad física con Acer, R50 y Arduino pendiente. Consulta [validación 0.3](docs/VALIDACION03.md) y [primera prueba](docs/PRUEBA_DE_HOY.md).

## Funciones

- **Atlas offline:** 13,372 objetos, 110 Messier y 8,920 estrellas. Búsqueda, favoritos, coordenadas propias y base SQLite de unos 5 MB. Carta de estrellas, sin fotografías de fondo.
- **Encuadre:** focal real, sensor R50 de 22.3 × 14.9 mm, rotación manual y mosaicos hasta 9 × 9. Campo aproximado, sin calibración de distorsión ni orientación medida de cámara.
- **Planificación:** altura/azimut, separación lunar, hora sidérea/HA y gráfica de esta noche. Ventanas aproximadas con altura ≥20°, oscuridad astronómica y separación lunar ≥20° cuando la Luna esté sobre el horizonte. Requiere coordenadas reales y reloj confirmado; no inventa una ubicación en Oaxaca.
- **Montura:** controlador propio INDI para OAT 1.13.x, puerto configurable, 19200/8N1 iniciales, identidad/versiones reales, mando N/S/E/O, cuatro velocidades, seguimiento, GoTo, parada y regreso al Home existente. El mando exige mantener pulsado y renovar su permiso cada 1.5 s, más latencia del enlace. PHD2 comparte INDI; solo el controlador abre el Arduino. Sin cambios de EEPROM, calibraciones o límites.
- **Secuencias:** exposición, ISO, cantidad y pausa por bloques; planes guardables. Light, Dark, Flat y Bias en planes separados para cambiar tapa o iluminación. No controla una tapa ni panel de flats.
- **Canon SD:** exige RAW+JPG, verifica ambos nombres y descarga solo su JPG. Caché de 64 MiB y JPG ≤16 MiB. Exposición fija o Bulb hasta 3600 s cuando USB anuncie comandos compatibles; Bulb sigue siendo experimental y requiere prueba física con la R50.
- **Centrado por JPG:** captura, resuelve, convierte ICRS a coordenadas aparentes de fecha, aplica corrección limitada y verifica. Normalmente ≤2° por corrección y hasta tres intentos; sin Sync ni redefinir Home. Se puede repetir entre fotos; no corrige estelas dentro de una exposición.
- **PHD2:** estado, gráfica, guiado/calibración si hace falta, dither y espera de estabilización confirmada. Cámara USB mediante INDI/V4L2 o simulador explícito. Acteck pendiente de prueba con estrellas en Linux.
- **Enfoque manual asistido:** HFR en JPG, rechazo de saturación e historial; ajusta físicamente el lente. No incluye enfocador motorizado.
- **Polar experimental:** tres fotos mientras giras solo AR, para estimar ajustes físicos de la base. Sin AutoPA ni búsqueda de sensores Home.
- **F8:** rojo de la aplicación y gamma global cuando X11 lo permita. **F11:** pantalla completa.

## Probar

Para la tarjeta ya grabada, utiliza `dist/AstroOne4All-0.3-actualizar`: cópiala al área visible de la USB, arranca la Live y ejecuta `bash actualizar.sh` desde esa carpeta. Comprueba primero la persistencia. Verifica hashes, instala una versión separada y conserva la aplicación 0.2 y las preferencias. No formatea discos ni modifica firmware. [Pasos completos](docs/PRUEBA_DE_HOY.md).

En este Windows, **Abrir vista previa.cmd** permite explorar la interfaz. El control de dispositivos y PHD2 incluido requieren Linux.

```sh
python3 -m astroall panel
python3 -m astroall doctor
python3 -m unittest discover -s tests -v
```

[Receta de construcción](docs/USB.md): Debian 13 amd64. La edición admite CPU **x86 de 64 bits**, 2 GB o más y BIOS/UEFI amd64. No es una imagen universal para ARM, CPU de 32 bits o cualquier UEFI de 32 bits. Gráficos, Wi-Fi y equipos de otras personas requieren controladores compatibles y pruebas específicas.

## Estado y licencias

Pruebas automáticas, simulación y dispositivos se registran por separado. Todavía no equivale a todo NINA. Pendientes: enfoque motorizado, rotador, orientación medida, meridian flip específico del OAT, recuperación automática y validación física prolongada. Una captura incierta se registra y **no se repite al reiniciar**.

Código propio MIT. Datos adaptados de OpenNGC/HYG **CC BY-SA 4.0**, con autores/revisiones/licencia en `astroall/data`. PHD2, INDI, libgphoto2, Astropy y Debian conservan sus licencias. [Fuentes](docs/FUENTES.md), [diseño](docs/DISENO.md), [equipo confirmado](docs/EQUIPO.md). Evidencias de 0.2 conservadas en `dist` y [VALIDACION.md](docs/VALIDACION.md).
