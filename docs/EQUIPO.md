# Equipo de referencia confirmado por el usuario

Actualizado el 2 de noviembre de 2026. Consultar este archivo y los dispositivos antes de sustituir datos por suposiciones.

## Computadora y almacenamiento

- Acer ES1-111, procesador antiguo no identificado, **2 GB de RAM**, sin disco interno.
- Arranque desde microSD **32 GB U3**, lector/hub USB 3.0, enlazado al único puerto funcional **USB 2.0** de la Acer.
- La SD de la **Canon es de 128 GB**, distinta de la tarjeta del sistema.

## Montura operativa

- OpenAstroTracker; Arduino Mega 2560 + RAMPS 1.4.
- Dos NEMA 17 **17HS4401**, 1.8°, 200 pasos/vuelta, corriente nominal 1.7 A. No confundir corriente nominal con corriente configurada del driver.
- Dos TMC2209 **standalone**, configurados físicamente **1/64**. Sin UART.
- Poleas GT2 de **16 dientes en ambos ejes**.
- **LCD Keypad Shield 1602**; conservar control autónomo.
- GPS NEO-6M: **TX → D17/RX2, Serial2**. D14/D15 no es la conexión actual.
- ESP32-C3 excluido. Sin AutoPA, encoders ni sensores de homing confirmados.
- No describen este equipo: 28BYJ-48, A4988, LCD 12864 ni TMC2209 por UART.

## Firmware y comunicación

HEX preparado: `OAT_Mega2560_RAMPS64_16T_GPS_D17.hex`; se comprobó en ese archivo la cadena **v1.13.22**. El archivo no está presente en esta carpeta de trabajo y no se ha inspeccionado aquí. Esa versión **no confirma** la realmente instalada.

El firmware preparado incorpora catálogo ampliado, centro de la Vía Láctea y «No visible ahora». Para regiones de la Vía Láctea se usa seguimiento sideral.

Control USB: **19200 baudios, 8N1** iniciales. 115200 se utilizó para cargar el HEX y **no** es el baud de control. Protocolo Meade/LX200 con extensiones OAT.

Consultar `:GVP#` (producto) y `:GVN#` (versión) y conservar respuestas reales. Cada comando tiene su formato de respuesta; no generalizar delimitadores. Un solo propietario del puerto serie. No borrar EEPROM, cambiar calibración/pasos/corrientes, redefinir Home ni alterar límites automáticamente. Posiciones calculadas por pasos no son mediciones de encoders.

## Tiempo y ubicación

Oaxaca, México. Zona inicial **America/Mexico_City**, UTC−6; conservarla entre sesiones y permitir cambiarla al viajar. El GPS entrega UTC. Cálculos en UTC, conversión de zona solo para presentación. No hay latitud/longitud exactas confirmadas; no sustituirlas por el centro de Oaxaca. Hora sidérea y HA requieren tiempo/ubicación/AR válidos.

## Canon

Canon EOS R50, SD 128 GB. Lentes: 18–45 mm, 50 mm f/1.8, 55–250 mm y **TTArtisan 10 mm f/2**, focal ya confirmada por el usuario.

RAW/CR3 en la SD; vistas ligeras solo si se confirma su comportamiento físico. RAW+JPG Med es el flujo experimental seleccionado. La Canon puede identificar y resolver entre exposiciones; no se supone autoguiado continuo mientras expone.

## Guiado aún por validar

- Acteck WM20 dio imagen en PHD2 por **Windows WDM**; no confirma soporte Linux ni capacidad de detectar estrellas.
- Placa aproximada **30.1 × 25.3 mm**, inscripción `PC_GC1054`; sensor sugerido, no identificado definitivamente.
- Objetivo acromático **52 mm de diámetro / 200 mm de focal** considerado para telescopio guía impreso; no consta comprado, montado ni enfocado.
- Nexxt AHIMPFI4U1 V1.1.12 no consiguió conversión a webcam: siguió Wi-Fi/Nexxt Home. No es guía operativa.
- Xiaomi 12 Pro experimental, sin validación de guiado.

## Producto

Aplicación propia en español, abierta a la comunidad, con modo nocturno rojo. Polar de tres puntos experimental del software; no es alineación de tres estrellas del firmware ni AutoPA. Distinguir implementación, simulación y validación real.
