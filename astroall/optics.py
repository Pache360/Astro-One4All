"""Optical field estimate for solving: real focal length, not crop-equivalent."""
import math

LENSES = {"Canon 55–250": (55, 250), "Canon 18–45": (18, 45),
          "50 mm f/1.8": (50, 50), "TTArtisan 10 mm f/2": (10, 10)}


def field_width(sensor_mm, focal_mm):
    if not (math.isfinite(sensor_mm) and 0 < sensor_mm <= 100
            and math.isfinite(focal_mm) and 0 < focal_mm <= 10000):
        raise ValueError("Ancho de sensor y focal deben ser valores positivos.")
    return math.degrees(2 * math.atan(sensor_mm / (2 * focal_mm)))
