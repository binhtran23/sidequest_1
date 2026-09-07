import random

from kaggle_environments.envs.kaggriculture.kaggriculture import CROPS

DIRECTIONS = {
    "NORTH": (0, -1),
    "SOUTH": (0, 1),
    "EAST": (1, 0),
    "WEST": (-1, 0),
}


def _in_bounds(x, y, board_size):
    return 0 <= x < board_size and 0 <= y < board_size


def _random_direction(fx, fy, tiles, board_size):
    options = []
    for name, (dx, dy) in DIRECTIONS.items():
        nx, ny = fx + dx, fy + dy
        if not _in_bounds(nx, ny, board_size):
            continue
        if tiles[ny][nx] == "LOCKED":
            continue
        options.append(name)
    return random.choice(options) if options else None


def _choose_farmer_action(farm, board_size, seeds):
    fx, fy = farm["farmer"]
    tile = farm["tiles"][fy][fx]
    choices = []

    if isinstance(tile, dict):
        kind = tile.get("kind")
        if kind == "PLANT":
            if tile.get("yield_units", 0) > 0:
                choices.append(["HARVEST"])
            if not tile.get("watered_today", True):
                choices.append(["WATER"])
        elif kind == "WEED":
            choices.append(["DIG"])
    elif tile is None:
        available_crops = [c for c, n in seeds.items() if n > 0]
        if available_crops:
            choices.append(["PLANT", random.choice(available_crops)])

    direction = _random_direction(fx, fy, farm["tiles"], board_size)
    if direction:
        choices.append([direction])

    choices.append(["PASS"])
    return random.choice(choices)


def _choose_market_actions(farm, shed, seeds):
    actions = []

    # Randomly sell a random product currently sitting in the shed.
    sellable = [p for p, n in shed.items() if n > 0]
    if sellable and random.random() < 0.5:
        product = random.choice(sellable)
        qty = random.randint(1, shed[product])
        actions.append(["SELL", product, qty])

    # Randomly buy a seed for a random crop if we can afford it.
    if random.random() < 0.5:
        affordable = [c for c, spec in CROPS.items() if farm["money"] >= spec["seed"]]
        if affordable:
            crop = random.choice(affordable)
            actions.append(["BUY_SEED", crop, 1])

    return actions


def agent(obs):
    farms = obs.get("farms", [])
    player = obs.get("player", 0)
    private = obs.get("private", {}) or {}

    if not farms or player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}

    farm = farms[player]
    board_size = len(farm["tiles"])
    seeds = private.get("seeds", {})
    shed = private.get("shed", {})

    farmer_action = _choose_farmer_action(farm, board_size, seeds)
    market_actions = _choose_market_actions(farm, shed, seeds)

    return {"farmer": farmer_action, "hands": [], "market": market_actions}
