# Astro One4All 0.3.12 · pantalla encendida y sesión sin suspensión

La tarjeta preparada instala esta actualización al arrancar normalmente con
persistencia. Comprueba **0.3.12**. Conserva fotografías, perfiles, planes y
registros. No formatea la SD ni modifica firmware o calibraciones.

## Energía de la Live

- Se desactiva el inicio automático de xscreensaver, conservando los demás
  programas de LXDE y una copia del archivo de inicio anterior.
- Se desactivan el protector X11 y el apagado automático del monitor (DPMS).
  Se aplica al iniciar la sesión y al abrir Astro One4All.
- La Live queda configurada sin suspensión ni hibernación; cerrar la tapa
  tampoco solicita suspensión. El apagado normal sigue disponible.
- El modo rojo F8 sigue disponible para reducir la luz de la pantalla.
  Estos ajustes son de esta Live; no cambian la configuración de energía de Windows.

El diagnóstico muestra el estado consultado de pantalla y la política de
suspensión, para poder comprobarlos en vez de asumir que se aplicaron.

## Qué muestran UnoMas y OtroMas

La montura aparece conectada y en seguimiento en ambos informes. La Canon
confirmó 55 fotos consecutivas con CR3 + JPG en su SD antes del error
`[-110] I/O in progress` durante otra captura fija de 5 segundos.

La pantalla negra que volvió inmediatamente al mover el ratón encaja con el
protector de pantalla. No demuestra una suspensión ni que ese fuera el origen
del error de cámara. El protector estaba presente en el inicio de LXDE.

## Captura incierta de la Canon

El disparo fijo ahora usa el contexto de diagnóstico nativo de libgphoto2 para
conservar también sus mensajes durante la captura. Ante el error -110 se explica
que la toma puede existir en la SD y la secuencia se detiene sin repetirla.
No se reinicia el USB ni se reconecta automáticamente la cámara o la montura.

Si vuelve a aparecer ese error, revisa la última foto y la luz de escritura de
la Canon antes de iniciar otro plan. Guarda un diagnóstico nuevo: el mensaje
del controlador permitirá investigar el problema de captura por separado.
Esta actualización no acredita haber eliminado la causa física del error -110.

## Prueba

1. Arranca la Acer y comprueba la versión. En Equipo y sistema → Comprobar
   sistema, revisa el bloque de energía del diagnóstico.
2. Deja la sesión sin tocar el teclado o ratón: la pantalla debe permanecer
   encendida. Mantén alimentación suficiente durante una sesión larga.
3. Prueba primero una captura corta y después una secuencia. Si se interrumpe,
   conserva el informe y comprueba la SD de la cámara antes de repetir.

Fuentes: documentación X.Org de X11/DPMS y opciones AllowSuspend/AllowHibernation de
systemd-sleep.conf. Las pruebas virtuales comprueban el estado X11 y la política;
el comportamiento físico de la Acer debe confirmarse durante una sesión real.
