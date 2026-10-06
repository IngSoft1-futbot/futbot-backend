"""
Comportamientos DEFAULT (confiables, corren dentro del motor).

Todos tienen la MISMA firma:  rol(jugador: dict, ctx: dict) -> None
asi el motor los puede llamar de forma generica segun el behavior_id.

ctx (lo arma el motor con armar_contexto):
  pelota      dict  {"x", "y", ...}
  companeros  list  jugadores del mismo equipo (sin el propio)
  rivales     list  jugadores del otro equipo
  arco_rival  dict  {"x", "y"}  centro del arco que ataca
  arco_propio dict  {"x", "y"}  centro del arco que defiende
  sentido     int   +1 si el equipo ataca hacia x = ANCHO, -1 si ataca hacia x = 0
  delta_t     float duracion de un tick (s)
  rng         random.Random del partido

El jugador puede traer "x0", "y0" (su posicion inicial de formacion). Si no
las trae, se usa su posicion actual como base.

IMPORTANTE: nada esta escrito para "el lado izquierdo": todo se calcula con
`sentido`, `arco_propio` y `arco_rival`, asi el equipo 2 (espejo) funciona igual.
"""
from . import primitivas

# --- Parametros de comportamiento (ajustar al balancear) ---
DESPEJE_X, DESPEJE_Y = 50.0, 30.0   # hacia donde despeja el defensor
RADIO_PRESION_DEFENSOR = 25.0       # el defensor presiona si la pelota esta a menos de esto de su base
RADIO_CAZA_DELANTERO = 10.0         # el delantero va a la pelota si esta a menos de esto
DISTANCIA_DESMARQUE = 15.0          # el delantero espera a esta distancia del arco rival
DISTANCIA_TIRO_MEDIO = 30.0         # el mediocampista tira al arco si esta a menos de esto
RADIO_PRESION_MEDIO = 20.0          # el mediocampista va a la pelota si es el mas cercano y esta a menos de esto
RADIO_LIBRE = 6.0                   # un companero esta "libre" si ningun rival esta a menos de esto


# =====================================================================
# AUXILIARES
# =====================================================================
def base(jugador: dict) -> tuple[float, float]:
    """Posicion base del jugador (formacion). Si no esta definida, la actual."""
    return jugador.get("x0", jugador["x"]), jugador.get("y0", jugador["y"])


def alcance(jugador: dict) -> float:
    """Radio de accion real del jugador (el mismo que usan las primitivas)."""
    return jugador["stats"]["control"] * primitivas.ESCALA_ALCANCE


def puede_golpear(jugador: dict, pelota: dict) -> bool:
    """True si la pelota esta dentro del alcance: ahi patear_pelota SI tiene efecto."""
    return primitivas.distancia(jugador["x"], jugador["y"], pelota["x"], pelota["y"]) <= alcance(jugador)


def mas_cercano(x: float, y: float, lista: list):
    """Elemento de `lista` mas cercano al punto (x, y), o None si esta vacia."""
    return min(lista, key=lambda j: primitivas.distancia(x, y, j["x"], j["y"]), default=None)


def soy_el_mas_cercano_a_la_pelota(jugador: dict, companeros: list, pelota: dict) -> bool:
    """Evita que todo el equipo corra a la pelota. Empate: gana el de menor y."""
    mio = (primitivas.distancia(jugador["x"], jugador["y"], pelota["x"], pelota["y"]), jugador["y"])
    return all(
        mio <= (primitivas.distancia(c["x"], c["y"], pelota["x"], pelota["y"]), c["y"])
        for c in companeros
    )


def esta_libre(candidato: dict, rivales: list) -> bool:
    return all(
        primitivas.distancia(candidato["x"], candidato["y"], r["x"], r["y"]) > RADIO_LIBRE
        for r in rivales
    )


def armar_contexto(jugador: dict, jugadores, pelota: dict, sentido: int, delta_t: float, rng) -> dict:
    """Arma el ctx que reciben los roles. `jugadores`: todos los jugadores en cancha."""
    todos = list(jugadores)
    mi_dueno = jugador.get("propietario")
    ancho, alto = primitivas.ANCHO_CANCHA, primitivas.ALTO_CANCHA
    x_rival, x_propio = (ancho, 0.0) if sentido > 0 else (0.0, ancho)
    return {
        "pelota": pelota,
        "companeros": [j for j in todos if j is not jugador and j.get("propietario") == mi_dueno],
        "rivales": [j for j in todos if j.get("propietario") != mi_dueno],
        "arco_rival": {"x": x_rival, "y": alto / 2},
        "arco_propio": {"x": x_propio, "y": alto / 2},
        "sentido": sentido,
        "delta_t": delta_t,
        "rng": rng,
    }


# =====================================================================
# ROLES (COMPORTAMIENTOS DEFAULT)
# =====================================================================
def rol_defensor(jugador: dict, ctx: dict) -> None:
    """
    Defensor: cuida SU zona (su posicion base), presiona y roba si hay peligro.
    Con la pelota: intenta salir jugando con un compañero libre, si no, despeja.
    """
    pelota, dt, sentido = ctx["pelota"], ctx["delta_t"], ctx["sentido"]
    bx, by = base(jugador)

    # 1. Con la pelota a su alcance: Salida limpia o pelotazo
    if puede_golpear(jugador, pelota):
        # Filtramos compañeros que estén desmarcados y más adelantados en la cancha
        libres = [
            c for c in ctx["companeros"]
            if esta_libre(c, ctx["rivales"]) and c["x"] * sentido > jugador["x"] * sentido
        ]
        
        if libres:
            # Si hay opciones, se la pasa al más adelantado para salir rápido
            destino = max(libres, key=lambda c: c["x"] * sentido)
            d = primitivas.distancia(jugador["x"], jugador["y"], destino["x"], destino["y"])
            fuerza = int(min(100, 30 + 2 * d))
            primitivas.pasar_pelota(jugador, destino, pelota, fuerza)
        else:
            # Si están todos marcados, no se complica y revienta
            primitivas.patear_pelota(jugador, pelota, DESPEJE_X, DESPEJE_Y, 100)
        return

    # 2. Peligro: la pelota entra en su zona de presion
    if primitivas.distancia(bx, by, pelota["x"], pelota["y"]) < RADIO_PRESION_DEFENSOR:
        rival = mas_cercano(jugador["x"], jugador["y"], ctx["rivales"])
        if rival is not None and primitivas.marcar_pelota(jugador, rival, pelota, ctx["rng"]):
            return
        # Sin rival, robo fallido o fuera de alcance: presiona la pelota
        primitivas.moverse_hacia(jugador, pelota["x"], pelota["y"], 90, dt)
        return

    # 3. Sin peligro: vuelve a su posicion y espera
    primitivas.mantener_posicion(jugador, bx, by, 5.0, pelota, dt)


def rol_delantero(jugador: dict, ctx: dict) -> None:
    """
    Delantero cazador: va a la pelota y patea al arco apenas la tiene;
    si esta lejos, se desmarca cerca del arco rival esperando un pase.
    """
    pelota, dt, arco, sentido = ctx["pelota"], ctx["delta_t"], ctx["arco_rival"], ctx["sentido"]

    # 1. Si la pelota esta a su alcance, remata al arco rival
    if puede_golpear(jugador, pelota):
        primitivas.patear_pelota(jugador, pelota, arco["x"], arco["y"], 100)
        return

    # 2. Pelota cerca: intenta robarla y, si no, corre hacia ella
    if primitivas.distancia(jugador["x"], jugador["y"], pelota["x"], pelota["y"]) < RADIO_CAZA_DELANTERO:
        rival = mas_cercano(jugador["x"], jugador["y"], ctx["rivales"])
        if rival is not None and primitivas.marcar_pelota(jugador, rival, pelota, ctx["rng"]):
            return
        primitivas.moverse_hacia(jugador, pelota["x"], pelota["y"], 100, dt)
        return

    # 3. Pelota lejos: se desmarca delante del arco rival (el signo depende del lado)
    x_desmarque = arco["x"] - DISTANCIA_DESMARQUE * sentido
    primitivas.moverse_hacia(jugador, x_desmarque, arco["y"], 70, dt)


def rol_mediocampista(jugador: dict, ctx: dict) -> None:
    """
    Mediocampista pasador: con la pelota tira si esta cerca del arco, si no pasa al
    companero libre mas adelantado (o juega largo); sin la pelota presiona solo si
    es el mas cercano y, si no, mantiene su zona.
    """
    pelota, dt, arco, sentido = ctx["pelota"], ctx["delta_t"], ctx["arco_rival"], ctx["sentido"]
    bx, by = base(jugador)

    # 1. Con la pelota a su alcance
    if puede_golpear(jugador, pelota):
        if primitivas.distancia(jugador["x"], jugador["y"], arco["x"], arco["y"]) <= DISTANCIA_TIRO_MEDIO:
            primitivas.patear_pelota(jugador, pelota, arco["x"], arco["y"], 100)
            return

        libres = [
            c for c in ctx["companeros"]
            if esta_libre(c, ctx["rivales"]) and c["x"] * sentido > jugador["x"] * sentido
        ]
        if libres:
            destino = max(libres, key=lambda c: c["x"] * sentido)   # el mas adelantado
            d = primitivas.distancia(jugador["x"], jugador["y"], destino["x"], destino["y"])
            # TODO: calibrar cuando exista la friccion de la pelota
            fuerza = int(min(100, 30 + 2 * d))
            primitivas.pasar_pelota(jugador, destino, pelota, fuerza)
        else:
            # Nadie libre adelante: juega largo hacia el arco rival, sin forzar
            primitivas.patear_pelota(jugador, pelota, arco["x"], arco["y"], 70)
        return

    # 2. Sin la pelota: solo presiona el mas cercano del equipo
    d_pelota = primitivas.distancia(jugador["x"], jugador["y"], pelota["x"], pelota["y"])
    if d_pelota < RADIO_PRESION_MEDIO and soy_el_mas_cercano_a_la_pelota(jugador, ctx["companeros"], pelota):
        rival = mas_cercano(jugador["x"], jugador["y"], ctx["rivales"])
        if rival is not None and primitivas.marcar_pelota(jugador, rival, pelota, ctx["rng"]):
            return
        primitivas.moverse_hacia(jugador, pelota["x"], pelota["y"], 100, dt)
        return

    # 3. Si no, mantiene su zona de mediocampo
    primitivas.mantener_posicion(jugador, bx, by, 8.0, pelota, dt)


# =====================================================================
# REGISTRO: behavior_id -> funcion
# (los ids tienen que coincidir con los que siembra la base de datos)
# =====================================================================
COMPORTAMIENTOS_DEFAULT = {
    0: rol_defensor,
    1: rol_delantero,
    2: rol_mediocampista,
}


def ejecutar_comportamiento(behavior_id: int, jugador: dict, ctx: dict) -> None:
    """Llama al rol default correspondiente. Si el id no existe, el jugador no hace nada."""
    rol = COMPORTAMIENTOS_DEFAULT.get(behavior_id)
    if rol is not None:
        rol(jugador, ctx)