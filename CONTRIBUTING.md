# Contribuir a Astro One4All

Queremos que una persona principiante pueda preparar una sesión de astrofotografía
con un portátil antiguo. La publicación 0.3.13 es experimental.

## Prioridades

- Sesiones prolongadas y diagnóstico del error Canon -110 tras una captura incierta.
- Comprobar puesta en estación con imágenes y una medición independiente bajo cielo real.
- Sensibilidad de cámaras guía con estrellas y convivencia con PHD2.
- Instalación desde una ISO limpia y pruebas en otras computadoras.
- Documentación sencilla y validación de nuevos modelos de cámaras y variantes OAT.

## Cambios de código

1. Explica el problema y el comportamiento esperado antes de ampliar el alcance.
2. Mantén un único propietario del puerto serie y conserva la conexión al navegar.
3. No cambies automáticamente EEPROM, pasos, corrientes, Home o límites del firmware.
4. Conserva originales en la SD de la cámara y acota las imágenes y cachés del ordenador.
5. No repitas automáticamente un disparo cuyo resultado sea incierto.
6. Ejecuta las pruebas apropiadas; describe qué usó simuladores y qué usó equipos físicos.

En Linux, con las dependencias indicadas en README:

```sh
xvfb-run -a python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Los guiones `integration_*.py` son pruebas de desarrollo adicionales y pueden requerir
servicios o imágenes de referencia específicos. No se ejecutan sobre equipos físicos
sin preparar y comprender el entorno.

## Reportar un problema

Incluye versión de Astro One4All, computadora/RAM, método de arranque, cámara,
firmware de montura, pasos para reproducir y mensaje exacto. Indica si el equipo
es real o simulado y qué sí funciona.

Los diagnósticos pueden contener coordenadas GPS, puertos y rutas de archivos.
Revísalos y oculta esos datos antes de publicarlos en un Issue. No adjuntes una
copia completa de tu SD ni fotografías privadas.

## Publicaciones

El código fuente puede compartirse como versión experimental. Una descarga de Live
debe construirse desde un entorno limpio, incluir sus avisos y fuentes de terceros
correspondientes y pasar una instalación nueva antes de anunciarse lista para todos.
