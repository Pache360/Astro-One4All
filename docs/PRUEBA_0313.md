# Astro One4All 0.3.13 · puesta en estación con imagen y retícula

El nuevo asistente usa la cámara principal o la cámara guía USB configurada.
No requiere cámara guía ni autoenfoque. Usa plate solving local; funciona sin red
cuando el campo tiene suficientes estrellas y los índices necesarios están en la Live.
Conserva el control de energía de 0.3.12 y la conexión compartida de la montura.

## Primera prueba, paso a paso

1. Conecta el OAT y lee hora/ubicación. Comprueba **fecha completa y hora UTC**,
   sobre todo si la batería del reloj de la Acer está agotada. El programa utiliza
   la ubicación guardada y la hora OAT importada; no supone un GPS independiente.
2. Abre **Alineación polar**. Elige Cámara principal, el formato de sensor y la
   focal real del lente. R50: APS-C Canon. Empieza con 2–5 s y estrellas enfocadas.
   Selecciona M, RAW + JPG y enfoque manual en la cámara.
3. Orienta aproximadamente la base hacia el polo y ajusta su altura a tu latitud.
   Apunta la cámara a un campo con estrellas, cerca de Polaris si la tienes visible.
   Una montura firme y razonablemente nivelada facilita los ajustes.
4. Marca la casilla de preparación y toma el primer punto. **Gira solo AR** con
   el mando del OAT; toma el segundo punto y repite para el tercero. Recomendado:
   15–30° por tramo, siempre dentro del recorrido libre. El software exige al
   menos 10° medidos. Mantén fijos DEC, cámara, zoom, trípode y ajustes de base.
5. Al completar los tres puntos aparece el error estimado y qué cambiar en la
   **base física**, en altitud y azimut. Mirando hacia el polo, sigue subir/bajar
   e izquierda/derecha. No son órdenes para los motores ni giros de un tornillo.
6. Ajusta un poco y pulsa **Comprobar ajuste**. También puedes activar el
   refresco: toma y resuelve una foto, espera y vuelve a medir. No es vídeo rápido.
   Al salir de esta pantalla se detiene el refresco y se conserva la referencia.
7. Cuando las marcas se acerquen, reinicia y repite los tres puntos para comprobar
   el resultado de forma independiente. La precisión bajo cielo real está pendiente
   de validar; no se presenta como AutoPA ni como alineación del firmware.

## Qué muestra la retícula

- **Cruz: polo celeste**, calculado para esa ubicación y momento.
- **Círculo: eje de AR medido** con las tres orientaciones resueltas.
- **Línea:** separación entre ambos. Se busca hacer coincidir esas marcas.
- **Polaris:** referencia aproximada de catálogo J2000. No debe centrarse como si
  fuera el polo. El asistente no identifica la estrella por brillo ni por un clic.
- Los anillos representan radios de 15, 30 y 60 minutos de arco alrededor del polo.
  Si un marcador queda fuera de la foto, una flecha señala el borde correspondiente.

Los grados/minutos indican movimiento angular de la base. El software no conoce
el paso de los tornillos ni cuántas vueltas necesita cada construcción OAT.

## Cámara guía y PHD2

La cámara guía es opcional. Conéctala y verifica su imagen desde Autoguiado antes
de elegirla en el asistente. El campo en grados puede dejarse vacío si no se conoce;
la búsqueda puede tardar más. No se inventa tamaño de sensor ni de píxel.

Detén primero las exposiciones y el guiado de PHD2. El asistente comprueba que no
esté guiando o calibrando y no toma control de ese trabajo automáticamente.
La Acteck sigue necesitando una prueba de sensibilidad con estrellas. Una webcam
en modo vídeo no adquiere necesariamente exposiciones de varios segundos aunque
se elija ese tiempo; depende del controlador. No se promete compatibilidad con un
modelo SVBONY que todavía no está definido.

Con la Canon cada medición deja RAW + JPG en la SD de la cámara. El ordenador
recibe solo el JPG en su caché acotada. El refresco toma fotos reales y consume
espacio en la SD. Un fallo detiene el refresco sin repetir automáticamente la toma.

## Límites y comprobaciones

Se usa la orientación WCS completa para que funcione también cuando el centro de
la imagen cambia muy poco al girar AR cerca del polo. Cada foto se transforma al
horizonte en su propio instante para no confundir el movimiento terrestre con el
error polar. Se rechazan giros insuficientes, ajustes incoherentes y cambios de
cámara, escala, tamaño, paridad, ubicación o DEC conocida de la montura.

Después de la tercera foto se conserva el eje en coordenadas de la cámara. Un
nuevo WCS actualiza su dirección después de mover la base. Esto exige que DEC,
el acoplamiento de la cámara y la óptica sigan fijos. Las posiciones OAT calculadas
ayudan a detectar cambios de DEC; no son mediciones de encoders. Cambios manuales,
flexión o holguras pueden invalidar la referencia: vuelve a medir los tres puntos.

La latencia USB, el enfoque, las distorsiones, la refracción cerca del horizonte
y la precisión del reloj limitan el resultado. No se garantiza una precisión por
el número de decimales mostrado. El diagnóstico exportado incluye las tres
mediciones y el último estado polar; una referencia no se restaura tras cerrar
la aplicación porque el montaje pudo haberse movido.

Pruebas de desarrollo: geometría sintética norte/sur, cámara centrada en el eje,
inversión de imagen, compensación temporal, actualización después del ajuste,
rechazo de incoherencias y navegación sin desconectar el controlador. La lectura
WCS se comprueba con Astrometry.net real y una imagen de demostración; eso no
acredita una alineación física en la Acer.

Referencias de método y formatos:
[SharpCap, alineación polar](https://docs.sharpcap.co.uk/4.1/9_PolarAlignment.htm),
[Astrometry.net, salida WCS](https://astrometry.net/doc/readme.html),
[Astropy, coordenadas de píxel](https://docs.astropy.org/en/stable/api/astropy.wcs.utils.pixel_to_skycoord.html),
[PHD2, herramientas de alineación](https://www.openphdguiding.org/man/Tutorials.htm).
