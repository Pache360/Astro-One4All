# Estado de la publicación 0.3.13

**Código fuente experimental para colaboradores y pruebas. No es una versión estable.**

| Función | Evidencia disponible | Pendiente |
| --- | --- | --- |
| Interfaz y navegación | 148 pruebas Linux; estado de equipo conservado entre pantallas | Uso prolongado en más computadoras |
| Arranque y actualización | BIOS/UEFI amd64 emulados, 2 GB; copia y actualización de la tarjeta del prototipo | ISO pública limpia y prueba de instalación nueva |
| OAT | Identidad v1.13.22 y seguimiento en registros físicos; propietario serie único | Otras variantes y sesiones prolongadas |
| Canon R50 | RAW/CR3 + JPG en SD; 55 fotos confirmadas antes de un error -110 | Resolver la causa del error y completar una noche de captura |
| Bulb | Implementación y pruebas de software | Confirmación física prolongada por modelo de cámara |
| Plate solving | Astrometry.net real, sin red, con imagen de referencia | Índices, enfoque y rendimiento adecuados a cada óptica |
| Polar visual | Geometría norte/sur, giro, paridad, WCS y refresco en simulación | Precisión bajo cielo real, flexión, refracción y latencia |
| Acteck WM20 | Fotogramas físicos en Windows; pruebas INDI/PHD2 con dispositivos virtuales | Estrellas y guiado físico en Linux |
| Otras cámaras / SVBONY | Adaptadores y configuración ampliables | Validar cada modelo; no existe compatibilidad universal confirmada |

La captura básica no depende de guía ni enfoque motorizado. Las posiciones que
informa el OAT proceden de sus cálculos de pasos; no se presentan como encoders.
La alineación polar requiere ajustes físicos de base; no convierte la montura en AutoPA.

Los resultados virtuales comprueban software y geometría. No garantizan el
comportamiento de un cable, cámara, hub USB, computadora o montaje diferente.

En esta publicación se entrega fuente y receta de construcción, no una copia de la
SD personal del desarrollador. El catálogo y sus avisos de licencia se conservan.
