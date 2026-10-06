import math
import random

# =====================================================================
# CONSTANTES Y LÍMITES FÍSICOS
# =====================================================================
ESCALA_VELOCIDAD = 0.08
ESCALA_ALCANCE = 0.05
ESCALA_TIRO = 0.3

ANCHO_CANCHA = 100.0
ALTO_CANCHA = 60.0

# =====================================================================
# 1. HERRAMIENTAS GEOMÉTRICAS Y VALIDACIÓN
# =====================================================================
def es_coordenada_valida(val) -> bool:
    """Evita la inyeccion de NaN, Infinitos, strings o booleanos."""
    return isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val)

def distancia(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)

def vector_normalizado(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]:
    d = distancia(x1, y1, x2, y2)
    if d == 0:
        return 0.0, 0.0
    return (x2 - x1) / d, (y2 - y1) / d

# =====================================================================
# 2. PRIMITIVAS DE ACCIÓN
# =====================================================================

def moverse_hacia(jugador: dict, x: float, y: float, porcentaje_velocidad: int, delta_t: float):
    """6.3.1 - Desplaza al jugador hacia (x, y) con clamping y protección estricta."""
    
    if not (es_coordenada_valida(x) and es_coordenada_valida(y) and es_coordenada_valida(porcentaje_velocidad)):
        return 

    p = max(0, min(100, float(porcentaje_velocidad)))
    
    vel_max = jugador["stats"]["speed"] * ESCALA_VELOCIDAD
    velocidad_actual = vel_max * (p / 100.0)
    paso_maximo = velocidad_actual * delta_t
    
    dist_objetivo = distancia(jugador["x"], jugador["y"], x, y)
    
    if dist_objetivo <= paso_maximo:
        jugador["x"], jugador["y"] = float(x), float(y)
    else:
        dx, dy = vector_normalizado(jugador["x"], jugador["y"], x, y)
        jugador["x"] += dx * paso_maximo
        jugador["y"] += dy * paso_maximo

    jugador["x"] = max(0.0, min(ANCHO_CANCHA, jugador["x"]))
    jugador["y"] = max(0.0, min(ALTO_CANCHA, jugador["y"]))


def mantener_posicion(jugador: dict, x: float, y: float, radio: float, pelota: dict, delta_t: float):
    """6.3.2 - Mantiene la posición y reacciona si la pelota invade su radio."""
    if not (es_coordenada_valida(x) and es_coordenada_valida(y) and es_coordenada_valida(radio)):
        return

    dist_pelota_a_zona = distancia(x, y, pelota["x"], pelota["y"])
    
    if dist_pelota_a_zona <= radio:
        moverse_hacia(jugador, pelota["x"], pelota["y"], 100, delta_t)
    else:
        if distancia(jugador["x"], jugador["y"], x, y) > 0.5:
            moverse_hacia(jugador, x, y, 80, delta_t)


def marcar_pelota(jugador: dict, rival: dict, pelota: dict, rng: random.Random) -> bool:
    """6.3.3 - Intenta robarle la pelota al rival."""
    if jugador.get("cooldown_accion", 0.0) > 0 or jugador.get("cooldown_robo", 0.0) > 0:
        return False

    if rival is jugador or rival.get("propietario") == jugador.get("propietario"):
        return False

    if distancia(rival["x"], rival["y"], pelota["x"], pelota["y"]) > 2.0:
        return False 

    radio_alcance = jugador["stats"]["control"] * ESCALA_ALCANCE
    dist_rival = distancia(jugador["x"], jugador["y"], rival["x"], rival["y"])
    
    if dist_rival > radio_alcance:
        return False 
        
    fuerza_mia = jugador["stats"]["strength"]
    fuerza_suya = rival["stats"]["strength"]
    
    if fuerza_mia > fuerza_suya:
        exito = True
    elif fuerza_mia < fuerza_suya:
        exito = False
    else:
        control_mio = jugador["stats"]["control"]
        control_suyo = rival["stats"]["control"]
        
        if control_mio > control_suyo:
            exito = True
        elif control_mio < control_suyo:
            exito = False
        else:
            exito = rng.choice([True, False])
    
    if exito:
        pelota["x"] = jugador["x"]
        pelota["y"] = jugador["y"]
        pelota["vx"] = 0.0
        pelota["vy"] = 0.0

        rival["cooldown_robo"] = 0.5 
        return True
    else:
        jugador["cooldown_robo"] = 1.0
        return False


def patear_pelota(jugador: dict, pelota: dict, x: float, y: float, porcentaje_fuerza: int) -> bool:
    """6.3.4 - Golpea la pelota hacia (x,y)."""

    if jugador.get("cooldown_accion", 0.0) > 0:
        return False

    if not (es_coordenada_valida(x) and es_coordenada_valida(y) and es_coordenada_valida(porcentaje_fuerza)):
        return False

    p = max(0, min(100, float(porcentaje_fuerza)))
    radio_alcance = jugador["stats"]["control"] * ESCALA_ALCANCE
    dist_pelota = distancia(jugador["x"], jugador["y"], pelota["x"], pelota["y"])
    
    if dist_pelota <= radio_alcance:
        dx, dy = vector_normalizado(pelota["x"], pelota["y"], x, y)
        
        velocidad_salida = jugador["stats"]["power"] * ESCALA_TIRO * (p / 100.0)
        pelota["vx"] = dx * velocidad_salida
        pelota["vy"] = dy * velocidad_salida
        
        segundos_castigo = max(0.2, 1.5 - (jugador["stats"]["agility"] * 0.013))
        jugador["cooldown_accion"] = segundos_castigo
        return True 
    
    return False


def pasar_pelota(jugador: dict, compañero: dict, pelota: dict, porcentaje_fuerza: int):
    """6.3.5 - Ejecuta un pase hacia la ubicación actual de un compañero."""
    if not compañero or compañero is jugador:
        return
        
    if compañero.get("propietario") != jugador.get("propietario"):
        return

    patear_pelota(jugador, pelota, compañero["x"], compañero["y"], porcentaje_fuerza)