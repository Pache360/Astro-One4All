# Astro One4All 0.3.6 · candidata de prueba

Expulsa la microSD con seguridad en Windows, colócala en la Acer y arranca la
entrada normal de Astro One4All con persistencia. El actualizador conserva los
perfiles, los registros, la versión anterior y las fotos de la Canon. No formatea.
Comprueba que la aplicación indique 0.3.6.

## Elige el equipo en Sistema

«Buscar equipo» enumera los dispositivos; selecciona el puerto de tu OAT y la
cámara principal, y pulsa «Guardar selección». La cámara principal elegida se
abre por su modelo y puerto USB: si ya no está disponible, se pide seleccionarla
otra vez y no se sustituye por otra. Guardar no inicia conexiones ni capturas.
«Conectar OAT» y «Comprobar cámara» permiten probar cada elemento.

La casilla «Tengo una cámara guía» es opcional. Aunque la marques, el plan no
exige guiado hasta activar esa opción después de calibrarlo en PHD2. Desmarcarla
desactiva guiado y dither del editor. El enfoque manual siempre está disponible.
La interfaz tiene botones redondeados accesibles con Tab/Enter/Espacio y un
emblema vectorial original de mapache que respeta el modo rojo de toda la pantalla.

La sesión básica funciona con OAT y cámara principal, enfoque manual y guiado
desactivado. No requiere Acteck, otra cámara guía ni autoenfoque. El registro de
adaptadores permite añadir otras marcas; el módulo PTP genérico es experimental
y solo permite capturas fijas si confirma sus capacidades. Véase CAMARAS_MODULOS.md.

## Montura y GPS

1. Enciende el OAT y espera «GPS sync'd» en su LCD. Conecta desde Montura usando
   el perfil propio Astro One4All OAT, tu puerto USB y 19200 baudios.
2. Se leen producto, versión, hora y ubicación mediante el mismo controlador.
   No se solicita otra adquisición GPS ni se cambian Home, calibraciones o EEPROM.
   El protocolo no informa un estado de fix actual: su confirmación sigue en el LCD.
3. En Montura comprueba fecha, hora y coordenadas. «Leer hora/ubicación» permite
   refrescarlas. En Atlas → Ubicación puedes cambiar zona horaria y desactivar la
   importación OAT para usar coordenadas y reloj del PC confirmados manualmente.
4. La hora OAT avanza mediante el reloj monotónico del arranque Linux; un RTC
   incorrecto de la Acer no gobierna los cálculos. Tras reiniciar, vuelve a leer OAT.
   TSL y HA del objeto se calculan con coordenadas de fecha. El HA polar informado
   por OAT se identifica por separado.
5. Cambia de pantalla: el indicador de montura permanece visible. Navegar suelta
   el mando manual, conservando la conexión y el seguimiento.

Se quitaron los pulsos de DTR de la aplicación y se desactivó HUPCL al abrir el
puerto. El primer acceso del controlador USB/kernel aún podría reiniciar ciertos
Mega/CH340: comprobarlo en el hardware es una condición pendiente, no una garantía
de esta versión. No se requiere modificar físicamente el Arduino para esta prueba.

## Atlas y propuesta de captura

- La lista muestra «No visible ahora» por debajo de 0°, «Muy cercano al horizonte»
  entre 0° y 20°, y «Visible» desde 20°. Se actualiza cada minuto y al seleccionar.
  Sin hora/ubicación válidas se indica lo que falta. La iluminación solar se muestra
  aparte: estar sobre el horizonte no significa que ya sea de noche.
- Selecciona APS-C Canon, APS-C o Full Frame. El encuadre y la propuesta usan ese
  tamaño. Se muestran recomendaciones para ambos formatos, exposición, cantidad,
  ISO e integración. Las ópticas APS-C no se presentan como lentes Full Frame.
- «Agregar al programa» crea el bloque editable y activa apuntar al iniciar. Revisa
  la focal física, apertura y enfoque; el programa no gira un zoom ni enfoca un
  lente manual. Las recomendaciones son puntos de partida conservadores para
  seguimiento sideral, no exposiciones óptimas medidas según tu cielo.
- Para tu Canon R50 usa **APS-C Canon**. Haz primero una toma de prueba, comprueba
  enfoque e histograma y luego inicia el plan. El GoTo requiere Home/límites válidos.
  Se rechazan movimientos y tomas de objetivos por debajo de 10°.
- El centrado con JPG y los mosaicos requieren índices de astrometry.net instalados
  para tu campo. El guiado es opcional y debe estar calibrado en PHD2. No se activa
  guiado o dither sin tu selección. Los RAW/CR3 permanecen en la SD de la Canon.

## Acteck y PHD2

Con PHD2 cerrado, pulsa Buscar cámaras y selecciona la USB identificada. Puede
llamarse «Integrated Camera» aunque sea la Acteck externa. Se conserva su identidad
USB pero se envía al controlador la ruta corta /dev/videoN, evitando el nombre largo
que el controlador de esta Live recortaba. Pulsa Conectar cámara y Ver imagen USB.

Después prepara el perfil con focal y tamaño de píxel reales, abre PHD2 y conecta
el equipo. La cámara integrada no sustituye automáticamente a la externa. El puerto
serie solo lo posee el controlador OAT; PHD2 comparte la montura por INDI.

## Alcance de la validación

Pruebas automatizadas y nativas Linux, navegación con OAT emulado, PHD2 oficial
calibrando/guiando/haciendo dither, capturas explícitamente simuladas y fotogramas
de una webcam virtual. El resultado y las limitaciones físicas están publicados en
CANDIDATA_JUEVES.md y en los informes qa036 de la distribución de desarrollo.

Tu registro confirma capturas físicas cortas con la R50 y la identidad real del OAT
v1.13.22. Falta verificar esta actualización en la Acer: reinicio al conectar, hora
GPS importada, continuidad al navegar, imagen Acteck, Bulb largo y guiado con estrellas.
El asistente polar de tres puntos sigue siendo experimental. Arquitectura amd64;
no se ha acreditado compatibilidad universal con cualquier PC/cámara.
