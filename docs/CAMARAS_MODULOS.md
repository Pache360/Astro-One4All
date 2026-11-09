# Cámaras y módulos

La sesión básica requiere la montura y la cámara principal. El enfoque manual y
el seguimiento sideral del OAT son suficientes para iniciar una secuencia. Cámara
guía, PHD2, dither, autoenfoque y centrado periódico con JPG son funciones opcionales;
el atlas no activa guiado por defecto. Las fotos para corregir encuadre se toman
entre exposiciones, no durante una exposición de la cámara principal.

## Adaptadores de captura

`camera_adapters.py` selecciona un adaptador por modelo. Todos ofrecen `inspect()`
y `capture_jpeg(cache, exposure, iso, stop, force_bulb)`; el motor de secuencias no
depende de la marca. El registro `register(CameraProfile(...))` permite incorporar
un adaptador de marca/SDK o un modelo específico sin reescribir Atlas, planes o OAT.

- Canon EOS R50 conserva su adaptador dedicado, incluidas las órdenes Bulb EOS.
  Las capturas cortas CR3+JPG en SD se comprobaron en el equipo del usuario. Bulb
  largo sigue pendiente de prueba física.
- Otras cámaras libgphoto2/PTP usan un adaptador experimental por capacidades.
  Solo dispara si se reconoce modo M, RAW+JPEG, destino de tarjeta confirmado y
  una velocidad fija anunciada de hasta 30 s. Reconoce extensiones RAW de varias
  marcas y descarga únicamente el JPG correspondiente a la misma toma.
- El adaptador genérico no inventa órdenes Bulb o de enfoque. Si falta una capacidad
  se explica qué falta y no se dispara. Detectar un modelo no acredita que ya esté
  probado físicamente. Las pruebas Nikon de esta versión son fixtures de protocolo.
- Los modelos USB sin control PTP/libgphoto2 o las cámaras astronómicas que guarden
  solo en el ordenador necesitan otro adaptador y una política de almacenamiento
  explícita. Esta versión no anuncia soporte universal ni simulación como validación
  de una marca. Conecta una sola cámara principal PTP a la vez.

La Acteck y una futura SVBONY pertenecen al camino de autoguiado INDI/PHD2. El modelo
exacto de SVBONY determinará el controlador y la configuración; no se da por validado
uno sin conocerlo ni se hace depender de él a la sesión básica.
