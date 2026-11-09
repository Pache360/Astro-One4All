# Astro One4All 0.3.9 · prueba de integración

Expulsa con seguridad la microSD en Windows y arranca la entrada normal de
Astro One4All con persistencia en la Acer. Esta tarjeta instala automáticamente
la actualización al arrancar. Comprueba que aparezca **0.3.9**. Conserva perfiles,
registros y versiones anteriores; no formatea ni modifica el firmware OAT.

## Primero, cámara y montura

1. Enciende el OAT y espera la confirmación GPS en su LCD. Conecta como siempre;
   para el Mega/RAMPS del proyecto se usan 19200 baudios. Cambiar de pantalla
   conserva la conexión y el seguimiento. No se requiere cámara guía ni autoenfoque.
2. Pon la R50 en fotografía, M, RAW + JPG y enfoque manual, con su SD instalada.
   En Sistema pulsa «Buscar equipo», selecciona tu cámara y guarda la selección.
   «Comprobar cámara» ahora identifica explícitamente el modelo y su puerto USB.
3. Prueba primero «Prueba foto · 1 s» y comprueba CR3 + JPG en la SD de la Canon.
   Después prueba Bulb de 3 s. Los originales permanecen en su tarjeta; solo se
   recibe el JPG ligero. No cambies cables ni apagues la cámara durante una toma.

La selección recupera un cambio de dirección USB solamente si encuentra una única
cámara del mismo modelo. Si hay varias, pide elegir. Un fallo de inicialización
ahora guarda los mensajes nativos del controlador y el estado USB. El registro
CanonError.json anterior no contenía esos detalles y no prueba una causa concreta.
Si sigue fallando, guarda un diagnóstico nuevo: no hace falta repetir muchas tomas.

## Cámara guía USB opcional

Con PHD2 cerrado, entra en Autoguiado, busca cámaras y selecciona la USB. La
Acteck puede llamarse **Integrated Camera**: ese nombre ya no hace que se oculte
como si fuera la integrada de la Acer. Se usa la identidad USB y el puerto real.

Pulsa **Probar imagen USB**. Este botón conecta la cámara elegida y solicita su
imagen. El éxito se confirma al recibir un fotograma, sin depender del eco del
interruptor de vídeo. Si una prueba anterior dejó vídeo abierto, una conexión
explícita puede reabrir únicamente esa cámara cuando PHD2 está cerrado.

Después prepara y abre PHD2. Cierra la vista previa antes de usarlo. Una imagen
diurna demuestra que llega vídeo; el enfoque y la sensibilidad con estrellas
todavía necesitan una prueba física. Puedes dejar la guía desactivada y fotografiar.

## Elegir un objeto y preparar las fotos

1. En Atlas, comprueba «Visible», «Muy cercano al horizonte» o «No visible ahora».
   Se necesitan hora y ubicación válidas. Estar visible no significa que sea de noche.
2. Selecciona el formato de sensor: **APS-C Canon** para la R50.
3. Consulta la recomendación de focal para APS-C y Full Frame. Cambia **Usaré / mm**
   por la focal real que tengas disponible, o pulsa **Usar recomendada**.
   Ajusta también físicamente el zoom: el programa no gira el lente.
4. La propuesta recalcula cantidad, segundos por foto, integración y campo según
   esa focal. Son valores iniciales conservadores: revisa enfoque e histograma.
5. Pulsa **Agregar al programa**. El plan conserva su focal y campo propios,
   aunque después selecciones otros objetos en Atlas. Revisa el bloque antes de iniciar.

## Plate solving sin cámara guía

En Sesión de fotos, la pestaña **Corrección JPG** permite activar
**Corregir con JPG de mi cámara**. Los nuevos planes del Atlas lo activan según
Configuración; el guiado PHD2 sigue siendo opcional y queda apagado por defecto.

Se comprueba el encuadre al iniciar y cada cierto número de fotos terminadas.
La revisión periódica intenta resolver el JPG de la última toma científica.
Si hace falta corregir, mueve la montura dentro de los límites y toma otra foto
para verificar. Esas fotos de comprobación son adicionales al bloque programado.
No corrige durante una exposición larga ni sustituye la alineación polar.

El motor astrometry.net e índices offline ya están incluidos. Para mover se
necesitan resolución válida, sitio/hora, Home y límites correctos. Si no puede
resolver o verificar el centrado, detiene la tarea con el motivo; no inventa coordenadas.

## Configuración

El botón **Configuración**, arriba en todas las pantallas, reúne sensor, focal,
ISO inicial, integración y pausas; corrección JPG, intervalo y tolerancia; inicio
en rojo y cámaras integradas. Se guardan entre sesiones. Los planes ya preparados
conservan sus ajustes. F8 activa el modo rojo y F11 la pantalla completa.

## Qué se ha verificado

Las pruebas distinguen código, dispositivos virtuales y hardware. Se comprueban
la inicialización con libgphoto2 nativa y sus mensajes de error, la recepción de
imágenes V4L2/INDI/PHD2, y navegación mientras se captura y guía en simulación.
No equivalen a conectar físicamente esta R50 o esta Acteck. Es necesario confirmar
en la Acer la foto de 1 s, Bulb, imagen USB y una sesión real antes de distribuir
la versión como estable. Consulta CANDIDATA_JUEVES.md para los pendientes.
