"""
Motor del amistoso 1v1

Dos capas:
  - MotorPartido: reglas del partido (estados, tiempos, pausas, posiciones).
    No usa red ni asyncio: se puede testear llamando a paso() en un for.
  - Amistoso: conexiones WebSocket + loop de ticks. Usa un MotorPartido.

Modulos que usa el motor:
  - comportamientos.py: los roles default (behavior_id -> funcion).
  - fisica.py: gol y rebotes de la pelota (funciones puras).
  - primitivas.py: lo usa comportamientos.py.

Para ligas/partidos concurrentes: un MotorPartido y un Amistoso (o su
equivalente) por partido, guardados en partidos_activos[match_id].
IMPORTANTE: partidos_activos vive en memoria de UN proceso -> no usar
uvicorn con --workers > 1.
"""
import asyncio
import inspect
import logging
import math
import random
from enum import Enum

from fastapi import WebSocket

from . import control_gol
from .control_gol import ALTO_CANCHA, ANCHO_CANCHA
from .comportamientos import COMPORTAMIENTOS_DEFAULT, armar_contexto, ejecutar_comportamiento

logger = logging.getLogger(__name__)

# --- TIEMPO ---
# f = ticks por segundo (entero), T = 1/f. Ticks por tiempo: N = D * f
FRECUENCIA = 20
TICK = 1 / FRECUENCIA
TOTAL_TIEMPOS = 4
DURACION_TIEMPO_S = 60   # D (s): valor de testeo, el minimo real es 60
DURACION_PAUSA_S = 15     # P (s): placeholder, se define mas adelante

# --- PELOTA ---
# Rozamiento: la velocidad se multiplica por K cada segundo (K en (0,1)).
# Por tick: v <- v * K^T. Distancia total de un tiro con velocidad inicial v0: d = v0 / (-ln K).
FRICCION_POR_SEGUNDO = 0.6
FRICCION_POR_TICK = FRICCION_POR_SEGUNDO ** TICK
VELOCIDAD_MINIMA_PELOTA = 0.2   # m/s: por debajo de esto la pelota se frena del todo

# En cada pausa, los jugadores vuelven a la formacion inicial y la pelota al centro.
REPONER_POSICIONES_EN_PAUSA = True

# Formacion para la mitad izquierda (el equipo 2 es el espejo).
# Solo POSICIONES: el motor las asigna por orden (el 1er jugador de la alineacion
# va al slot 0, etc.). Los stats y el behavior los elige el usuario al crear el jugador.
FORMACION_TRIANGULO = [
    {"rol": "defensor_superior", "x": 20.0, "y": 15.0},
    {"rol": "defensor_inferior", "x": 20.0, "y": 45.0},
    {"rol": "delantero", "x": 40.0, "y": 30.0},
]

# --- ALINEACION (lo que trae cada usuario: sus 3 titulares) ---
# Formato de cada jugador:
#   {"player_id": int, "nombre": str, "behavior_id": int,
#    "stats": {"speed", "control", "strength", "power", "agility"}}
STATS_JUGADOR = ("speed", "control", "strength", "power", "agility")
STAT_MIN, STAT_MAX = 20, 100

# SOLO PARA PRUEBAS (Postman / tests): se usa si no se pasa un cargador de alineaciones.
ALINEACION_PRUEBA = [
    {"player_id": 0, "nombre": "Defensor A", "behavior_id": 0,
     "stats": {"speed": 50, "control": 60, "strength": 80, "power": 60, "agility": 50}},
    {"player_id": 0, "nombre": "Defensor B", "behavior_id": 0,
     "stats": {"speed": 50, "control": 60, "strength": 80, "power": 60, "agility": 50}},
    {"player_id": 0, "nombre": "Delantero", "behavior_id": 1,
     "stats": {"speed": 70, "control": 55, "strength": 50, "power": 75, "agility": 50}},
]


def validar_alineacion(alineacion) -> list[dict]:
    """
    Chequea que la alineacion sea usable por el motor y devuelve una COPIA limpia.
    Lanza ValueError con un mensaje legible. (La regla de los 300 puntos ya la valida
    la creacion del jugador; aca solo se protege al motor de datos rotos.)
    """
    if not isinstance(alineacion, (list, tuple)) or len(alineacion) != len(FORMACION_TRIANGULO):
        raise ValueError(f"La alineación debe tener exactamente {len(FORMACION_TRIANGULO)} jugadores.")
    limpia = []
    for i, pj in enumerate(alineacion):
        if not isinstance(pj, dict):
            raise ValueError(f"Jugador {i}: formato inválido.")
        stats = pj.get("stats")
        if not isinstance(stats, dict) or set(stats) != set(STATS_JUGADOR):
            raise ValueError(f"Jugador {i}: stats incompletos (se esperan {', '.join(STATS_JUGADOR)}).")
        for nombre_stat, v in stats.items():
            es_num = isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
            if not es_num or not (STAT_MIN <= v <= STAT_MAX):
                raise ValueError(f"Jugador {i}: {nombre_stat} debe estar entre {STAT_MIN} y {STAT_MAX}.")
        bid = pj.get("behavior_id")
        if not isinstance(bid, int) or isinstance(bid, bool):
            raise ValueError(f"Jugador {i}: behavior_id inválido.")
        # Por ahora solo existen los roles default. TODO: reemplazar por la BD.
        if bid not in COMPORTAMIENTOS_DEFAULT:
            raise ValueError(f"Jugador {i}: el comportamiento {bid} no existe.")
        limpia.append({
            "player_id": pj.get("player_id"),
            "nombre": str(pj.get("nombre", f"Jugador {i}")),
            "behavior_id": bid,
            "stats": dict(stats),
        })
    return limpia


class Estado(Enum):
    ESPERANDO = "esperando"
    EN_JUEGO = "en_juego"
    PAUSA = "pausa"
    FINALIZADO = "finalizado"


partidos_activos: dict[int, "Amistoso"] = {}


# =====================================================================
# MOTOR PURO (sin red)
# =====================================================================
class MotorPartido:
    def __init__(
        self,
        id_eq1: int,
        id_eq2: int,
        duracion_tiempo_s: float = DURACION_TIEMPO_S,
        duracion_pausa_s: float = DURACION_PAUSA_S,
        semilla: int | None = None,
        alineacion_eq1: list[dict] | None = None,
        alineacion_eq2: list[dict] | None = None,
    ):
        self.ids = (id_eq1, id_eq2)
        # Alineaciones: las que trae cada usuario (stats + behavior). Si no se pasan: las de prueba.
        self._alineaciones = (
            validar_alineacion(alineacion_eq1 if alineacion_eq1 is not None else ALINEACION_PRUEBA),
            validar_alineacion(alineacion_eq2 if alineacion_eq2 is not None else ALINEACION_PRUEBA),
        )
        self.ticks_por_tiempo = round(duracion_tiempo_s * FRECUENCIA)
        self.ticks_por_pausa = round(duracion_pausa_s * FRECUENCIA)
        self.rng = random.Random(semilla)   # un RNG por partido (con semilla -> reproducible)

        self.estado = Estado.EN_JUEGO
        self.tiempo_actual = 1
        self.ticks_en_tiempo = 0
        self.ticks_en_pausa = 0

        self.marcador = {"eq1": 0, "eq2": 0}
        self.eventos: list[dict] = []  # Cola de mensajes del sistema (goles, etc.)

        self.pelota: dict = {}
        self.jugadores: dict[str, dict] = {}
        self._inicial: dict[str, tuple[float, float]] = {}

        self._asignar_formacion()   # una sola vez: propietarios, stats y behaviors
        self.reponer_posiciones()   # posiciones y pelota

    # ---------- formacion y posiciones ----------
    def _asignar_formacion(self):
        for n, (propietario, espejo, alineacion) in enumerate(
            zip(self.ids, (False, True), self._alineaciones), start=1
        ):
            for idx, (pos, pj) in enumerate(zip(FORMACION_TRIANGULO, alineacion)):
                clave = f"eq{n}_jug_{idx}"
                x = ANCHO_CANCHA - pos["x"] if espejo else pos["x"]
                self._inicial[clave] = (x, pos["y"])
                self.jugadores[clave] = {
                    "propietario": propietario,
                    "sentido": -1 if espejo else 1,   # +1: ataca hacia x = ANCHO; -1: hacia x = 0
                    "x": x,
                    "y": pos["y"],
                    "x0": x,                          # posicion de formacion (la usan los roles)
                    "y0": pos["y"],
                    "player_id": pj["player_id"],     # id del jugador en la BD
                    "nombre": pj["nombre"],
                    "behavior_id": pj["behavior_id"],
                    "stats": dict(pj["stats"]),       # copia: cada jugador tiene la suya
                    "cooldown_accion": 0.0,
                    "cooldown_robo": 0.0,
                }

    def reponer_posiciones(self):
        """Vuelve a la formacion inicial SIN tocar los behavior_id. Pelota al centro, quieta."""
        self.pelota = {"x": ANCHO_CANCHA / 2, "y": ALTO_CANCHA / 2, "vx": 0.0, "vy": 0.0}
        for clave, jug in self.jugadores.items():
            jug["x"], jug["y"] = self._inicial[clave]
            jug["cooldown_accion"] = 0.0
            jug["cooldown_robo"] = 0.0

    # ---------- un tick ----------
    def paso(self) -> str | None:
        """
        Avanza un tick segun el estado. Devuelve un evento (str) si hubo una
        transicion: "pausa", "reanuda" o "fin"; None si no paso nada especial.
        """
        if self.estado == Estado.EN_JUEGO:
            self._aplicar_behaviors()
            self._mover_pelota()
            self.ticks_en_tiempo += 1
            if self.ticks_en_tiempo >= self.ticks_por_tiempo:
                return self._fin_de_tiempo()
        elif self.estado == Estado.PAUSA:
            self.ticks_en_pausa += 1
            if self.ticks_en_pausa >= self.ticks_por_pausa:
                return self._reanudar()
        return None

    def _aplicar_behaviors(self):
        """
        Por cada jugador: baja sus cooldowns en T y ejecuta su behavior (rol default).
        El orden cambia en cada tick (rng del partido) para que ningun equipo tenga
        ventaja siempre que dos jugadores disputan la misma pelota.

        TODO (behaviors de usuarios): correrlos sandboxeados, con timeout y una copia
        de solo lectura del estado; validar lo que devuelven antes de aplicarlo.
        """
        claves = list(self.jugadores)
        self.rng.shuffle(claves)
        for clave in claves:
            jug = self.jugadores[clave]
            for cd in ("cooldown_accion", "cooldown_robo"):
                if jug[cd] > 0.0:
                    jug[cd] = max(0.0, jug[cd] - TICK)
            try:
                ctx = armar_contexto(jug, self.jugadores.values(), self.pelota,
                                     jug["sentido"], TICK, self.rng)
                ejecutar_comportamiento(jug["behavior_id"], jug, ctx)
            except Exception:
                # Un bug en un rol no debe tirar el partido: ese jugador se queda quieto este tick.
                logger.exception("Fallo el behavior %s de %s", jug["behavior_id"], clave)

    # ---------- pelota y goles ----------
    def _mover_pelota(self):
        """Integra la pelota (x += vx*T), resuelve gol/rebotes (fisica.py) y aplica rozamiento."""
        p = self.pelota
        x_prev, y_prev = p["x"], p["y"]
        p["x"] += p["vx"] * TICK
        p["y"] += p["vy"] * TICK

        resultado = control_gol.resolver_pelota(p, x_prev, y_prev)
        if resultado == "gol_eq1":
            self._registrar_gol(self.ids[0])
            return
        if resultado == "gol_eq2":
            self._registrar_gol(self.ids[1])
            return

        p["vx"] *= FRICCION_POR_TICK
        p["vy"] *= FRICCION_POR_TICK
        if math.hypot(p["vx"], p["vy"]) < VELOCIDAD_MINIMA_PELOTA:
            p["vx"] = p["vy"] = 0.0

    def _registrar_gol(self, id_equipo: int):
        clave_eq = "eq1" if id_equipo == self.ids[0] else "eq2"
        self.marcador[clave_eq] += 1

        num_eq = "1" if clave_eq == "eq1" else "2"
        self.eventos.append({
            "tipo": "sys",
            "mensaje": f"¡Gol! El Equipo {num_eq} anota. Marcador: {self.marcador['eq1']} - {self.marcador['eq2']}"
        })
        self.reponer_posiciones()   # saque de centro

    def _fin_de_tiempo(self) -> str:
        if self.tiempo_actual == TOTAL_TIEMPOS:
            self.estado = Estado.FINALIZADO
            return "fin"
        self.estado = Estado.PAUSA
        self.ticks_en_pausa = 0
        if REPONER_POSICIONES_EN_PAUSA:
            self.reponer_posiciones()
        return "pausa"

    def _reanudar(self) -> str:
        self.tiempo_actual += 1
        self.ticks_en_tiempo = 0
        self.estado = Estado.EN_JUEGO
        return "reanuda"

    # ---------- acciones de los jugadores ----------
    def cambiar_comportamiento(self, user_id: int, player_id, behavior_id) -> tuple[bool, str]:

        if self.estado == Estado.FINALIZADO:
            return False, "El partido ya finalizó."
        jug = self.jugadores.get(player_id) if isinstance(player_id, str) else None
        if jug is None:
            return False, "El jugador indicado no existe."
        if jug["propietario"] != user_id:
            return False, "Ese jugador no es tuyo."
        if not isinstance(behavior_id, int) or isinstance(behavior_id, bool):
            return False, "behavior_id inválido."
        # Por ahora solo existen los roles default. TODO: reemplazar por la BD
        # (que el behavior exista y pertenezca a user_id).
        if behavior_id not in COMPORTAMIENTOS_DEFAULT:
            return False, "Ese comportamiento no existe."
        jug["behavior_id"] = behavior_id
        return True, "Comportamiento actualizado."

    # ---------- lo que ven los clientes ----------
    def snapshot(self) -> dict:
        pausa_restante = 0.0
        if self.estado == Estado.PAUSA:
            pausa_restante = round((self.ticks_por_pausa - self.ticks_en_pausa) / FRECUENCIA, 2)
        return {
            "tipo": "estado",
            "estado": self.estado.value,
            "tiempo": self.tiempo_actual,
            "tick": self.ticks_en_tiempo,
            "ticks_por_tiempo": self.ticks_por_tiempo,
            "pausa_restante_s": pausa_restante,
            "marcador": self.marcador,
            "pelota": {k: round(v, 2) for k, v in self.pelota.items()},
            "jugadores": {
                clave: {
                    "propietario": j["propietario"],
                    "player_id": j["player_id"],
                    "nombre": j["nombre"],
                    "x": round(j["x"], 2),
                    "y": round(j["y"], 2),
                    "behavior_id": j["behavior_id"],
                }
                for clave, j in self.jugadores.items()
            },
        }


# =====================================================================
# CONEXIONES + LOOP
# =====================================================================
class Amistoso:
    def __init__(self, match_id: int, cargar_alineacion=None):
        """
        cargar_alineacion(user_id) -> lista de 3 jugadores (ver formato arriba), sync o async.
        Es el enganche con la BD: trae los titulares del usuario con sus stats y behaviors.
        Si es None se usa ALINEACION_PRUEBA (solo para pruebas).
        """
        self.match_id = match_id
        self.cargar_alineacion = cargar_alineacion
        self.alineaciones: dict[int, list[dict]] = {}   # user_id -> alineacion ya validada
        self.jugadores_ws: dict[int, WebSocket] = {}   # max. 2
        self.espectadores_ws: set[WebSocket] = set()
        self.motor: MotorPartido | None = None          # se crea al unirse el 2do jugador
        self.tarea: asyncio.Task | None = None          # referencia fuerte a la tarea

    @property
    def estado_partido(self) -> Estado:
        return Estado.ESPERANDO if self.motor is None else self.motor.estado

    async def _cargar_alineacion(self, user_id: int) -> list[dict]:
        if self.cargar_alineacion is None:
            return validar_alineacion(ALINEACION_PRUEBA)
        if inspect.iscoroutinefunction(self.cargar_alineacion):
            datos = await self.cargar_alineacion(user_id)
        else:
            # funcion sincrona (ej. consulta a la BD): en un hilo para no frenar el loop de ticks
            datos = await asyncio.to_thread(self.cargar_alineacion, user_id)
        return validar_alineacion(datos)

    # ---------- entrada / salida de conexiones ----------
    async def unir_jugador(self, user_id: int, ws: WebSocket) -> str:
        """Devuelve el rol asignado: "jugador" o "espectador"."""
        if self.estado_partido == Estado.FINALIZADO:
            await ws.send_json({"tipo": "error", "mensaje": "El partido ya finalizó."})
            return "espectador"

        # --- LÓGICA DE RECONEXIÓN ---
        # Si el partido ya arrancó y el usuario es uno de los dueños originales:
        if self.motor is not None and user_id in self.motor.ids:
            self.jugadores_ws[user_id] = ws
            await ws.send_json({"tipo": "sys", "mensaje": f"¡Reconectado exitosamente al partido {self.match_id}!"})
            return "jugador"
        # ----------------------------

        es_jugador = user_id in self.jugadores_ws or (
            self.motor is None and len(self.jugadores_ws) < 2
        )
        if not es_jugador:
            # Primero el saludo y despues el registro: si el socket ya esta caido,
            # la excepcion sube al endpoint y no queda un espectador fantasma.
            await ws.send_json({"tipo": "sys", "mensaje": f"Mirando el partido {self.match_id}."})
            self.espectadores_ws.add(ws)
            return "espectador"

        # Se carga y valida la alineacion ANTES de aceptarlo como jugador: si esta rota,
        # el error le llega a el (y no al rival) y no queda ocupando el lugar.
        if user_id not in self.alineaciones:
            try:
                self.alineaciones[user_id] = await self._cargar_alineacion(user_id)
            except Exception as e:
                # 1. Filtramos: ValueError es culpa del usuario, lo demás es error interno
                if isinstance(e, ValueError):
                    detalle = str(e)
                else:
                    logger.exception("Fallo al cargar la alineación del usuario %s", user_id)
                    detalle = "error interno, intentá de nuevo."
                
                # 2. En lugar de cerrarle el socket, le avisamos y lo metemos a mirar
                await ws.send_json({"tipo": "sys", "mensaje": f"Pasando a modo espectador. Motivo: {detalle}"})
                self.espectadores_ws.add(ws)
                return "espectador"

        self.jugadores_ws[user_id] = ws
        await ws.send_json(
            {"tipo": "sys", "mensaje": f"Conectado al partido {self.match_id}. Esperando rival..."}
        )

        if len(self.jugadores_ws) == 2 and self.motor is None:
            id_eq1, id_eq2 = list(self.jugadores_ws)
            self.motor = MotorPartido(
                id_eq1, id_eq2,
                alineacion_eq1=self.alineaciones[id_eq1],
                alineacion_eq2=self.alineaciones[id_eq2],
            )
            self.tarea = asyncio.create_task(self.correr())
        return "jugador"

    async def desconectar(self, user_id: int, ws: WebSocket):
        if ws in self.espectadores_ws:
            self.espectadores_ws.discard(ws)
            return
        if self.jugadores_ws.get(user_id) is not ws:
            return  # esta conexion ya habia sido reemplazada

        # Removemos el socket del jugador, pero EL MOTOR SIGUE CORRIENDO
        self.jugadores_ws.pop(user_id, None)

        if self.motor is None:
            if not self.jugadores_ws and not self.espectadores_ws:
                partidos_activos.pop(self.match_id, None)
            return

        # Avisamos a los demás que este usuario se desconectó temporalmente
        if self.motor.estado != Estado.FINALIZADO:
            await self.difundir({"tipo": "sys", "mensaje": f"El jugador {user_id} se desconectó (esperando reconexión)."})

    async def difundir(self, mensaje: dict):
        destinos_jugadores = [(uid, ws) for uid, ws in self.jugadores_ws.items()]
        destinos_espectadores = [(None, ws) for ws in self.espectadores_ws]

        async def enviar_jugador(uid, ws):
            if ws is None:
                return
            try:
                await ws.send_json(mensaje)
            except Exception:
                # Si falla el envío, removemos el socket pero el partido SIGUE
                # (solo si no fue reemplazado por una reconexión mientras tanto)
                if self.jugadores_ws.get(uid) is ws:
                    self.jugadores_ws.pop(uid, None)

        async def enviar_espectador(ws):
            try:
                await ws.send_json(mensaje)
            except Exception:
                self.espectadores_ws.discard(ws)

        tareas = [enviar_jugador(uid, ws) for uid, ws in destinos_jugadores]
        tareas += [enviar_espectador(ws) for ws in destinos_espectadores]

        if tareas:
            await asyncio.gather(*tareas)

    # ---------- loop principal ----------
    async def correr(self):
        motor = self.motor
        await self.difundir({"tipo": "sys", "mensaje": "¡El partido ha comenzado!"})

        loop = asyncio.get_running_loop()
        proximo = loop.time()
        try:
            while motor.estado != Estado.FINALIZADO:
                evento = motor.paso()

                # --- PROCESAMIENTO DE EVENTOS (Goles, etc.) ---
                if motor.eventos:
                    for evt in motor.eventos:
                        await self.difundir(evt)
                    motor.eventos.clear()
                await self.difundir(motor.snapshot())

                if evento == "pausa":
                    await self.difundir({
                        "tipo": "sys",
                        "mensaje": f"Pausa táctica ({DURACION_PAUSA_S} s). "
                                   f"Comienza el tiempo {motor.tiempo_actual + 1}. Enviá tus cambios.",
                    })
                elif evento == "reanuda":
                    await self.difundir({"tipo": "sys", "mensaje": f"Comienza el tiempo {motor.tiempo_actual}."})
                elif evento == "fin":
                    await self.difundir({"tipo": "sys", "mensaje": "¡Fin del partido!"})

                # Deadline fijo: no acumula la deriva del procesamiento.
                proximo += TICK
                ahora = loop.time()
                if proximo < ahora - 1.0:     # nos atrasamos demasiado: no hacer rafaga
                    proximo = ahora
                await asyncio.sleep(max(0.0, proximo - ahora))
        finally:
            partidos_activos.pop(self.match_id, None)

    # ---------- comandos de los jugadores ----------
    def aplicar_accion(self, user_id: int, comando: dict) -> tuple[bool, str]:
        if self.motor is None:
            return False, "El partido todavía no empezó."
        if not isinstance(comando, dict):
            return False, "Formato de comando inválido."

        nombre = comando.get("comando")
        if nombre == "cambiar_comportamiento":
            player_id = comando.get("player_id")
            behavior_id = comando.get("behavior_id")
            
            # 1. Intentamos hacer el cambio en el motor
            exito, msg = self.motor.cambiar_comportamiento(user_id, player_id, behavior_id)
            
            # 2. Si salió bien, agregamos un evento al motor para que lo difunda a todos
            if exito:
                # Buscamos el nombre del jugador para hacerlo más personalizado
                jugador_info = self.motor.jugadores.get(player_id, {})
                nombre_jugador = jugador_info.get("nombre", "un jugador")
                
                self.motor.eventos.append({
                    "tipo": "sys",
                    "mensaje": f"El equipo del usuario {user_id} cambió la táctica del jugador '{nombre_jugador}'."
                })
                
            return exito, msg
        if nombre == "sustituir":
            # Solo aplica a ligas (3 suplentes, 1 por pausa). No implementado en amistosos.
            return False, "Las sustituciones no están disponibles en amistosos."
        return False, "Comando desconocido."
    