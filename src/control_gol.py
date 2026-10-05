"""
Fisica de la pelota: gol y rebotes. Funciones puras, sin red ni estado del partido.

Convenciones (las mismas que el resto del proyecto):
  - Cancha de ANCHO x ALTO = 100 x 60. x va de 0 a 100, y de 0 a 60.
  - Equipo 1 ataca hacia x = ANCHO (arco derecho). Equipo 2 ataca hacia x = 0.
  - Cada arco esta centrado en y = ALTO/2 y mide LARGO_ARCO = 20,
    o sea ocupa y en [20, 40] sobre la linea de fondo.
"""
import math

ANCHO_CANCHA = 100.0
ALTO_CANCHA = 60.0
LARGO_ARCO = 20.0
ARCO_Y_MIN = (ALTO_CANCHA - LARGO_ARCO) / 2   # 20
ARCO_Y_MAX = (ALTO_CANCHA + LARGO_ARCO) / 2   # 40


def _cruce_en_y(x_prev: float, y_prev: float, x: float, y: float, x_linea: float) -> float:
    """
    y por donde el segmento (x_prev,y_prev)->(x,y) corta la recta x = x_linea.
    Interpolacion lineal: t = (x_linea - x_prev) / (x - x_prev),  y_c = y_prev + t * (y - y_prev).
    Precondicion: x != x_prev (si cruza la linea, x_prev y x estan a lados distintos).
    """
    t = (x_linea - x_prev) / (x - x_prev)
    return y_prev + t * (y - y_prev)


def esta_en_arco(y: float) -> bool:
    """True si una pelota que pasa por la linea de fondo con ordenada y entra al arco (palo incluido)."""
    return ARCO_Y_MIN <= y <= ARCO_Y_MAX


def resolver_pelota(pelota: dict, x_prev: float, y_prev: float):
    """
    Se llama DESPUES de mover la pelota (pelota["x"], pelota["y"] ya son la posicion nueva)
    y recibe la posicion del tick anterior.

    Usa el SEGMENTO recorrido en el tick, no solo el punto final: asi un tiro rapido
    no "atraviesa" el arco entre un tick y el siguiente.

    Devuelve:
      "gol_eq1"  la pelota cruzo x = ANCHO dentro de [20, 40]
      "gol_eq2"  la pelota cruzo x = 0 dentro de [20, 40]
      None       no hubo gol (si toco una pared, la pelota rebota y queda dentro de la cancha)

    En caso de gol NO corrige la posicion: el motor reubica todo (saque de centro).
    """
    x, y = pelota["x"], pelota["y"]
    if not all(math.isfinite(v) for v in (x, y, x_prev, y_prev)):
        pelota["x"], pelota["y"] = ANCHO_CANCHA / 2, ALTO_CANCHA / 2
        pelota["vx"] = pelota["vy"] = 0.0
        return None

    # 1) Lineas de fondo: gol o rebote
    if x >= ANCHO_CANCHA and x_prev < ANCHO_CANCHA:
        if esta_en_arco(_cruce_en_y(x_prev, y_prev, x, y, ANCHO_CANCHA)):
            return "gol_eq1"
    elif x <= 0.0 and x_prev > 0.0:
        if esta_en_arco(_cruce_en_y(x_prev, y_prev, x, y, 0.0)):
            return "gol_eq2"

    # 2) Rebotes (fondo fuera del arco y bandas). Reflejo: x' = 2L - x si se paso de L.
    if x > ANCHO_CANCHA:
        pelota["x"], pelota["vx"] = 2 * ANCHO_CANCHA - x, -pelota.get("vx", 0.0)
    elif x < 0.0:
        pelota["x"], pelota["vx"] = -x, -pelota.get("vx", 0.0)
    if y > ALTO_CANCHA:
        pelota["y"], pelota["vy"] = 2 * ALTO_CANCHA - y, -pelota.get("vy", 0.0)
    elif y < 0.0:
        pelota["y"], pelota["vy"] = -y, -pelota.get("vy", 0.0)

    # Por si un tiro enorme se paso de rosca en el reflejo
    pelota["x"] = min(ANCHO_CANCHA, max(0.0, pelota["x"]))
    pelota["y"] = min(ALTO_CANCHA, max(0.0, pelota["y"]))
    return None