# Astro One4All 0.3.10 · pruebas sin objetivo y webcam

La tarjeta preparada instala esta actualización al arrancar normalmente con
persistencia. Comprueba que aparezca 0.3.10. No se formatea ni se borran perfiles,
planes guardados, registros o fotografías. Expulsa la tarjeta con seguridad en Windows.

## Volver al campo actual

En Sesión de fotos pulsa **Quitar objetivo**, junto al botón Atlas. Retira el
objeto o mosaico cargado, desactiva GoTo inicial y corrección JPG de ese objetivo.
Conserva exposición, cantidad, ISO, bloques y fotos. No mueve ni desconecta la
montura. Mientras haya una tarea activa, primero hay que detenerla y esperar.

**Foto de prueba · 1 s**, debajo de la imagen, toma una sola foto independiente
del plan, incluso si hay un objetivo del atlas cargado. No ejecuta GoTo ni plate
solving. Pide confirmar el disparo real y respeta RAW/CR3 + JPG en la SD de la
Canon. El plan queda preparado para continuar después. El enfoque es manual.

Para secuencias de prueba, quita el objetivo, escribe por ejemplo 5 fotos de 2 s,
desactiva Exigir guiado PHD2 si estaba activado y pulsa Iniciar plan. El equipo
básico sigue siendo OAT + cámara principal; guía y autoenfoque son opcionales.

## Qué mostró UltimasPruebas

La R50 completó cinco tomas consecutivas y una prueba corta, confirmando CR3 +
JPG en su SD y solo JPG recibido. La montura compartida por INDI se identificó
correctamente. El plan posterior se detuvo al no resolver su campo en 90 s;
no debe interpretarse como avería de disparo. Para resolver se necesitan estrellas,
enfoque suficiente y la focal real. Las tomas diurnas sirven para probar captura.

La Acteck se abrió en el nodo USB correcto, pero estaba usando Motion-JPEG a
1280 × 720. INDI 1.9.9 puede enviar ese vídeo como `.stream_jpg` incluso si se
ha elegido RAW como codificador: la vista previa anterior lo rechazaba.

Ahora se admite ese JPEG con límites de tamaño y conversión monocroma para la
vista previa. Al conectar una webcam, se prefiere YUYV y 640 × 480 cuando la
cámara anuncia esas opciones, para usar una ruta compatible con el vídeo RAW
de PHD2 y reducir la carga del USB 2.0. No cambia formatos durante el guiado activo.

Con PHD2 cerrado: Autoguiado → Buscar cámaras → elegir la USB → **Probar imagen
USB**. Después abre PHD2 y conecta sus equipos. Consultar/gráfica requiere que
PHD2 ya esté abierto y tenga su servidor activado. Las pruebas de vídeo virtual
no demuestran sensibilidad ni enfoque de la Acteck con estrellas.

## Prioridad recomendada

1. Consolidar OAT + R50: varias tomas cortas mientras se navega por Atlas y Montura.
2. De noche, comprobar enfoque y plate solving con el JPG de estrellas; después
   probar el centrado y la corrección periódica sin guía.
3. Mantener la Acteck como prueba opcional. Antes de comprar una SVBONY, comprobar
   el modelo concreto y su controlador Linux/PHD2. La marca por sí sola no asegura
   compatibilidad con esta distribución.

El registro muestra además una fecha OAT adelantada respecto a la fecha de esta
revisión. Antes de una sesión real, contrasta la fecha completa y la hora en
Montura con la fecha local correcta; un mensaje GPS sync'd no sustituye esa
comprobación. La aplicación no cambia automáticamente la fecha del firmware.

Fuentes de protocolo: código oficial INDI 1.9.9,
https://github.com/indilib/indi/blob/v1.9.9/libs/indibase/stream/streammanager.cpp
y manual PHD2, https://openphdguiding.org/man/MainScreen.htm.
La webcam convencional puede tener una exposición física corta aunque PHD2
muestre un intervalo mayor. Las exposiciones largas requieren validación real.
