from schemas import Player


def verify_player(player: Player) -> bool:

    pacss = player.pacss_atributes

    if not (20 <= pacss.power <= 100):
        return False

    if not (20 <= pacss.agility <= 100):
        return False

    if not (20 <= pacss.control <= 100):
        return False

    if not (20 <= pacss.speed <= 100):
        return False

    if not (20 <= pacss.strength <= 100):
        return False

    if (
        pacss.power
        + pacss.agility
        + pacss.control
        + pacss.speed
        + pacss.strength
        != 300
    ):
        return False

    return True
