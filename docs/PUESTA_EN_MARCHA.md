# Puesta en marcha

## Estado de las pruebas

Se han comprobado lógica de selección de JPG, rechazo de RAW como descarga, límites de caché, errores de cámara simulada, coordenadas y fallos del solver con sustitutos. Los resultados de las pruebas automáticas se documentan al entregar. No se han conectado dispositivos reales ni iniciado el sistema en la Acer.

## Montura propia mediante INDI

El perfil inicial es **19200 baudios, 8N1**, configurable; 115200 corresponde a programación del HEX y no a control. Antes de usar INDI, con OAT **en reposo** y el puerto libre, «Identificar OAT» o `astroall oat-info --port /dev/serial/by-id/...` consulta únicamente `:GVP#` y `:GVN#`, ambos con respuesta terminada en `#`, y registra las respuestas en `~/.local/state/astroall/oat-identity.jsonl`. La versión instalada se toma de esa respuesta, no del HEX preparado v1.13.22. Esta consulta es una acción separada; todavía no se integra automáticamente en la conexión INDI.

Se comprueba que el puerto esté libre y se solicita exclusividad. DTR/RTS se preparan inactivos, pero abrir el USB de un Mega puede provocar un reset por su circuito/driver; por eso esta identificación inicial se prueba **sin una sesión de seguimiento o exposición activa**. No cambia EEPROM ni calibraciones. No se abren simultáneamente la consulta directa y el controlador INDI.

Desde «Montura», inicia un controlador instalado, usa Detectar y selecciona puerto `/dev/serial/by-id/...` y baudios que coincidan con tu firmware. `indi_lx200_OpenAstroTech` es el controlador específico cuando esté disponible. Debian incluye una versión antigua de INDI; la alternativa `indi_lx200gps` usa compatibilidad documentada por OAT, con menos funciones. No se afirma compatibilidad del perfil hasta probarlo con la versión concreta del firmware.

La aplicación no cambia el firmware ni pasos/corrientes/calibración de RAMPS. El usuario ya confirmó que el OAT funciona. Para GoTo deben estar configurados home, hora, ubicación y límites en el controlador. **Las coordenadas del GoTo son AR de fecha en horas y DEC de fecha en grados.** Los centros resueltos de JPG se expresan en ICRS/J2000 y no deben copiarse directamente a ese campo.

«PARAR montura» usa una conexión INDI separada para no esperar a que finalice un solve. Es una solicitud de parada al firmware; no equivale a cortar alimentación. El programa no mata automáticamente el controlador al cerrar, porque la montura podría seguir siguiendo.

## Prueba de originales en SD

Haz una sola foto corta con tarjeta en la R50, modo M y RAW+JPG Med. Comprueba físicamente el par en la SD y que la caché del ordenador solo contiene el JPG. La aplicación verifica nombres y tamaños por protocolo, pero la inspección física confirma el comportamiento de esa cámara/firmware.

Después: varias fotos, pausa, parada entre fotos, tarjeta llena, desconexión de cámara y reinicio. Ante error se detiene sin disparar otra vez automáticamente. Bulb y exposición mayor de 30 s todavía no están implementados en el adaptador.

## Asistente polar propio

Calcula el campo en «Mis lentes». Introduce ubicación real en grados decimales; oeste es negativo. El reloj UTC debe ser correcto, importante en un portátil viejo cuya batería de reloj puede estar agotada.

El asistente toma/resuelve tres fotos. Entre ellas gira únicamente AR con el mando existente del OAT, dentro de su recorrido libre, separando encuadres al menos 5°. Mantén fijos DEC, objetivo y trípode. Se transforman los centros al horizonte local para compensar el giro terrestre entre mediciones; se estima el eje como normal al plano de esos tres vectores.

El resultado indica cuánto modificar **la base física** en altitud y azimut, no un GoTo. No hay refresco gráfico ni garantía de precisión astrométrica hasta contrastarlo bajo cielo real. La hora de cada foto se estima desde el disparo del ordenador; la latencia USB aún no se calibra. Tres puntos siempre definen un plano: errores de medida, flexión, distorsión y movimientos de DEC pueden producir un resultado engañoso; se debe volver a medir después del ajuste.

## Guiado y recentrado

El sistema todavía no integra cámara guía ni autoguiado continuo. La Nexxt del chat anterior no se considera cámara guía funcional mientras no se confirme su conversión y sensibilidad.

Resolver JPG sucesivos permite comparar encuadres. La corrección posterior puede recuperar el objetivo para la próxima exposición; no repara estrellas movidas en la anterior. El ciclo automático de captura/solve/recentrado/verificación aún está pendiente. No hay una promesa de sustituir una cámara guía con exposiciones largas de la R50.
