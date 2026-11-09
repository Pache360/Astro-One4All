# Candidata para el jueves 12 de noviembre de 2026

Objetivo: una distribución de prueba que complete una sesión integrada en la
Acer ES1-111 (2 GB, USB 2.0), con límites y compatibilidad publicados. La versión
de trabajo es 0.3.13; no debe anunciarse estable basándose solo en pruebas unitarias.

## Criterios antes de distribuir

- Una única conexión OAT a 19200 8N1 permanece al navegar por todas las pantallas.
  Navegar suelta el movimiento manual y conserva el seguimiento sideral.
- El estado real de la montura es visible desde Atlas, captura y autoguiado.
- Un error tardío de una vista cerrada se registra sin detener las actualizaciones
  de equipo ni el progreso de captura.
- La cámara guía elegida entrega fotogramas monocromos a PHD2. Los demás clientes
  INDI no reciben imágenes y no abren de nuevo el puerto del Arduino.
- PHD2 realiza calibración, guiado y dither en su simulador oficial; una secuencia
  que exige guiado espera su estabilización y se detiene si deja de estar listo.
- La secuencia de cámara principal sigue funcionando mientras se navega por Atlas,
  montura y guiado. Las tomas interrumpidas no se cuentan como completas ni se repiten.
- El arranque offline con persistencia funciona en BIOS y UEFI con 2 GB. Los
  perfiles sobreviven a un reinicio y las actualizaciones no retroceden de versión.
- Se publica una tabla que distingue pruebas virtuales de pruebas físicas.

## Verificación física necesaria

Conservar las comprobaciones anteriores de Canon R50 (CR3 + JPG en su SD, solo
JPG recibido) e identidad OAT v1.13.22. Leer los nuevos registros de la Acer antes
de atribuir el fallo de navegación a la pantalla o al enlace USB.

Probar con el equipo del usuario: navegación durante seguimiento, imagen de la
Acteck identificada, Bulb de 3 s y una exposición larga, cierre del obturador y
apagado normal. La sensibilidad de la Acteck y el guiado con estrellas no pueden
acreditarse mediante una webcam virtual.

El asistente polar de tres puntos conserva su etiqueta experimental. No implica
AutoPA, encoders ni sensores de Home instalados en el OAT.
La 0.3.13 añade WCS completo, imagen con retícula y refresco del ajuste manual.
Debe contrastarse bajo cielo real repitiendo una medición independiente.

## Evidencia de trabajo

UnoMas.json y OtroMas.json de la 0.3.11 muestran 55 fotos consecutivas y después
Canon -110 I/O in progress, manteniendo OAT conectado y siguiendo. El usuario
confirma pantalla negra con retorno inmediato al mover el ratón. La 0.3.12
desactiva xscreensaver/DPMS y la suspensión de la Live; no presenta esa prevención
como solución demostrada al error Canon. Se conserva el contexto nativo durante
el disparo fijo y se detiene sin reintentar una exposición incierta.

La 0.3.11 corrige un caso no cubierto por la 0.3.10: tras cambiar formato, la
Acteck negoció YUYV 640 × 480 pero el controlador mantuvo CCD/streaming a
1280 × 720. La imagen automática recuperada confirma mosaicos y franjas. Se
reaplica la resolución aunque figure ya seleccionada y se verifica geometría
antes de transmitir. Los fallos conservan el tamaño solicitado y el anunciado.
La misma cámara física produjo imágenes completas en Windows en tres modos;
los fotogramas privados no forman parte de los paquetes de distribución.

UltimasPruebas.json de la 0.3.9 confirma cinco fotos consecutivas de la R50 y una
prueba de 1 s, CR3 + JPG en SD y solo JPG recibido. Identifica correctamente la
Acteck externa: el fallo de vista previa es de formato con Motion-JPEG activo,
no una prueba de webcam averiada. La 0.3.10 admite `.stream_jpg` con límites y
prefiere YUYV/640 × 480 disponibles en la conexión explícita UVC. Los cambios de
formato se rechazan durante streaming activo. Es necesaria prueba física de imagen.

Quitar objetivo elimina la asociación del plan al Atlas y desactiva su GoTo y
centrado, conservando bloques y ajustes. No opera dispositivos. Se rechaza durante
una tarea activa. Foto de prueba de 1 s ejecuta solo el disparo de cámara, sin
ejecutar movimientos ni plate solving del plan cargado.

La 0.3.9 parte del registro físico CanonError.json: la Canon falló al inicializar
USB, antes de configurar exposición o disparar; el error genérico no identifica
la causa. La aplicación ahora enumera y elige explícitamente modelo/puerto, conserva
los mensajes de libgphoto2 y registra el fallo también desde Comprobar cámara.
La prueba nativa con libgphoto2 2.5.33 verifica inicialización y conservación del
mensaje real de error; no conecta una Canon física ni dispara fotografías.

El mismo registro muestra vídeo sin confirmar y selección posterior de la webcam
interna. La clasificación ya no descarta una USB por llamarse Integrated Camera.
Probar imagen USB usa la selección actual y confirma un fotograma recibido, sin
esperar un eco del interruptor de streaming. El botón momentáneo de lectura GPS
acepta su retorno normal a Off, evitando un aviso falso de desconexión.

La focal recomendada y la focal usada son independientes. El plan guarda su propio
campo de resolución y la revisión periódica reutiliza el JPG científico terminado;
si corrige, captura una verificación nueva. Configuración reúne las preferencias.

La reproducción básica en la 0.3.4 mantuvo el mismo socket, la identidad y el
seguimiento durante 21 cambios de pantalla. Eso no reproduce todavía el fallo
reportado en la Acer; se requiere contrastarlo con su registro y con la prueba
conjunta de PHD2, cámara y navegación.

La 0.3.5 añade un indicador global de montura, evita acumular manejadores de foco
y protege el procesamiento de actualizaciones frente a callbacks de vistas ya
destruidas. No reconecta ni reinicia automáticamente el Arduino.

La prueba conjunta 0.3.5 completó calibración, guiado y dither reales del simulador
oficial PHD2, seis capturas explícitamente simuladas y navegación por todas las
pantallas con un solo propietario serie OAT emulado. Una prueba separada recibió
vista previa y tres fotogramas PHD2 de Linux vivid usando el mismo alias USB largo
de la Acteck; el controlador recibió /dev/video8. No acredita imagen física Acteck.

El registro «Acutal Estado.json» identifica la Acteck como USB 0c45:64ab con nombre
«Integrated Camera» y confirma el recorte del último carácter del alias by-id.
La 0.3.5 conserva ese alias como identidad, pero abre el nodo corto verificado.

Se leen fecha, hora, desfase UTC y sitio OAT sin iniciar adquisición GPS. La hora
se ancla al arranque Linux y caduca tras reiniciar, evitando usar el RTC incorrecto
de la Acer. No existe un getter de fix GPS en este protocolo: el LCD confirma fix.
Las leyendas de visibilidad se calculan con Astropy offline, con estado independiente
para la iluminación solar. El HA del objeto usa AR aparente, separado del HA polar OAT.

Los planes del atlas prellenan un bloque editable y el GoTo inicial, con propuestas
APS-C/Full Frame conservadoras. El guiado queda apagado por defecto y no se requiere
autoenfoque. El registro de adaptadores conserva la ruta R50 y admite un adaptador
PTP experimental para otras marcas: requiere capacidades de almacenamiento/captura
confirmadas y limita esa ruta a exposición fija; no acredita cámaras no probadas.

Eliminar los cambios DTR y limpiar HUPCL mitiga reinicios de aplicación, pero no
demuestra que el kernel/CH340 no reinicie el primer acceso físico. Esta condición y
la continuidad real en la Acer siguen siendo puertas de validación de hardware.

La 0.3.6 añade selección persistente de cámara principal por modelo/puerto USB,
montura y cámara guía opcional en Sistema. Guardar no abre hardware ni mueve la
montura; el módulo de captura respeta la cámara elegida y rechaza sustituciones.
El enfoque es manual. La marca mapache se dibuja con vectores nativos y los
botones redondeados conservan foco de teclado, estado desactivado y modo rojo.

La 0.3.7 añade perfiles de placa OAT independientes, sin manipular su electrónica.
No se permite cambiar de perfil mientras la montura está conectada/conectándose.
La navegación no activa perfiles ni reabre el puerto. La fuente de hora de otro
OAT se invalida al cambiar de perfil, manteniendo la zona horaria del usuario.

El motor real astrometry.net 0.97 y doce índices 2MASS 08–19 están incluidos en
la Live. El adaptador de la aplicación resolvió la referencia oficial apod4 de
Astrometry.net offline en unos 17 s en el emulador. La imagen ajena de referencia
no se distribuye en el paquete ni se presenta como foto del usuario.

La 0.3.8 aplica el mismo reloj UTC a la marca temporal de las capturas. Esto evita
arrastrar el RTC incorrecto a las herramientas que consumen el instante de la foto.
