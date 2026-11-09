"""Red-only X11 gamma ramps with restoration; UI theme also works off Linux."""
import ctypes as ct
import ctypes.util
import os


def red_ramps(original, brightness=.35):
    if not 0 < brightness <= 1:
        raise ValueError("Brillo inválido.")
    return [int(v * brightness) for v in original[0]], [0]*len(original[0]), [0]*len(original[0])


class NightScreen:
    def __init__(self):
        self.display = None
        self.saved = None

    def enable(self):
        if self.display:
            return
        if os.name != "posix" or not os.environ.get("DISPLAY"):
            raise RuntimeError("Rojo global disponible en Linux/X11; el tema de la app sí está activo.")
        self.x11 = ct.CDLL(ctypes.util.find_library("X11") or "libX11.so.6")
        self.vm = ct.CDLL(ctypes.util.find_library("Xxf86vm") or "libXxf86vm.so.1")
        self.x11.XOpenDisplay.argtypes = [ct.c_char_p]
        self.x11.XOpenDisplay.restype = ct.c_void_p
        self.x11.XDefaultScreen.argtypes = [ct.c_void_p]
        self.x11.XDefaultScreen.restype = ct.c_int
        self.x11.XCloseDisplay.argtypes = [ct.c_void_p]
        self.x11.XFlush.argtypes = [ct.c_void_p]
        pointer = ct.POINTER(ct.c_ushort)
        self.vm.XF86VidModeGetGammaRampSize.argtypes = [ct.c_void_p, ct.c_int, ct.POINTER(ct.c_int)]
        self.vm.XF86VidModeGetGammaRamp.argtypes = [ct.c_void_p, ct.c_int, ct.c_int, pointer, pointer, pointer]
        self.vm.XF86VidModeSetGammaRamp.argtypes = [ct.c_void_p, ct.c_int, ct.c_int, pointer, pointer, pointer]
        self.vm.XF86VidModeQueryExtension.argtypes = [ct.c_void_p, ct.POINTER(ct.c_int), ct.POINTER(ct.c_int)]
        self.display = self.x11.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError("No se pudo abrir la pantalla X11.")
        self.screen = self.x11.XDefaultScreen(self.display)
        size = ct.c_int()
        try:
            event_base, error_base = ct.c_int(), ct.c_int()
            if not self.vm.XF86VidModeQueryExtension(self.display, ct.byref(event_base), ct.byref(error_base)):
                raise RuntimeError("La pantalla X11 no ofrece ajuste global de gamma; se conserva el tema rojo de la app.")
            if not self.vm.XF86VidModeGetGammaRampSize(self.display, self.screen, ct.byref(size)) or not 1 <= size.value <= 65536:
                raise RuntimeError("El controlador no permite modificar la rampa de color.")
            self.array = ct.c_ushort * size.value
            arrays = [self.array() for _ in range(3)]
            if not self.vm.XF86VidModeGetGammaRamp(self.display, self.screen, size.value, *arrays):
                raise RuntimeError("No se pudo guardar el color original.")
            self.saved = [list(a) for a in arrays]
            adjusted = [self.array(*channel) for channel in red_ramps(self.saved)]
            if not self.vm.XF86VidModeSetGammaRamp(self.display, self.screen, size.value, *adjusted):
                raise RuntimeError("El controlador rechazó el rojo global.")
            self.x11.XFlush(self.display)
        except Exception:
            self.restore()
            raise

    def restore(self):
        if self.display:
            try:
                if self.saved:
                    arrays = [self.array(*channel) for channel in self.saved]
                    self.vm.XF86VidModeSetGammaRamp(self.display, self.screen, len(arrays[0]), *arrays)
                    self.x11.XFlush(self.display)
            finally:
                self.x11.XCloseDisplay(self.display)
                self.display = None
                self.saved = None
