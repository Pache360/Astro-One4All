# Construir una Live de Astro One4All

La publicación inicial de GitHub entrega **código fuente experimental**. Todavía
no hay una ISO pública 0.3.13 lista para grabar. No uses imágenes de máquinas
virtuales o copias de tarjetas personales como si fueran el instalador público.

## Construcción para colaboradores

Utiliza un equipo o una máquina virtual de desarrollo con **Debian 13 trixie amd64**,
conexión a Internet y espacio para descargar paquetes y construir la imagen.
La computadora de construcción no tiene que ser el portátil de 2 GB destinado al campo.

Desde una copia limpia del repositorio:

```sh
sudo bash system/build-live.sh
```

La receta exige una carpeta de trabajo vacía. Instala herramientas de construcción
en el equipo anfitrión, descarga fuentes de libgphoto2/PHD2 con sus hashes fijados,
compila dentro de la Live y ejecuta comprobaciones. **No graba una unidad USB.**

El resultado previsto es `build/live/live-image-amd64.hybrid.iso`, sus sumas y registros.
Una compilación terminada debe validarse antes de distribuir esa ISO.
Las versiones Debian no están fijadas a un snapshot; no se promete reproducción
binaria exacta de las imágenes usadas durante el desarrollo.

## Persistencia y grabación

El equipo de referencia usa microSD de 32 GB y aproximadamente 16 GB de persistencia.
Los originales van en la SD de la cámara, mientras las preferencias, índices y
JPG de caché acotada se guardan en el medio del sistema.

Debian Live necesita un volumen ext4 etiquetado `persistence` y un archivo
`persistence.conf` en su raíz con:

```text
/ union
```

La receta incluye el parámetro de arranque `persistence`. La aplicación bloquea
captura desde una Live sin persistencia reconocida. La grabación de una ISO borra
el medio elegido; identifica ese medio antes de iniciar el grabador.

## Antes de ofrecer una ISO a otras personas

1. Construir desde fuentes sin perfiles, redes, claves, fotos ni registros personales.
2. Verificar sumas y conservar avisos y fuentes correspondientes de los componentes incluidos.
3. Grabar una tarjeta nueva y comprobar persistencia después de reiniciar.
4. Probar BIOS/UEFI amd64, interfaz y periféricos en equipos físicos representativos.
5. Comprobar cámara, cierre de exposición, seguimiento y navegación antes de una sesión larga.
6. Publicar arquitectura, limitaciones, instrucciones y estado experimental junto a la descarga.

Secure Boot, UEFI de 32 bits, ARM y cualquier modelo de computadora no se consideran
compatibilidad confirmada. USB 2.0 comparte ancho de banda entre sistema y dispositivos.

Las imágenes antiguas de desarrollo no son una ISO actualizada 0.3.13.
