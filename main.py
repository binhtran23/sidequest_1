"""Astra: market forecasting, capital allocation, and coordinated farm routes.

Submission is self-contained and uses only the Python standard library.
"""

import math

# seed, first production age, last production age, interval, harvest cap
CROPS = {
    "WHEAT": (10, 2, 4, 0, 6),
    "CARROT": (20, 2, 3, 0, 4),
    "TOMATO": (50, 8, 11, 1, 4),
    "STRAWBERRY": (100, 10, 16, 2, 4),
    "MELON": (80, 10, 12, 0, 6),
}
# cost, first production age, interval, storage cap, product, structure
ANIMALS = {
    "GOOSE": (300, 4, 1, 4, "EGG", "COOP"),
    "COW": (400, 8, 2, 6, "MILK", "PASTURE"),
    "SHEEP": (500, 6, 3, 6, "WOOL", "PASTURE"),
}
PARAMS = {
    "WHEAT": (25, 400, "sqrt", 0.8, "log", 0.2),
    "CARROT": (35, 450, "hinge", 1.0, "sqrt", 0.7),
    "TOMATO": (60, 200, "hinge", 0.4, "sqrt", 0.6),
    "STRAWBERRY": (120, 100, "sqrt", 0.7, "linear", 1.6),
    "MELON": (250, 300, "log", 0.2, "sq", 3.6),
    "EGG": (50, 332, "hinge", 0.4, "log", 0.2),
    "MILK": (160, 122, "sqrt", 0.6, "linear", 1.6),
    "WOOL": (200, 105, "log", 0.2, "sq", 3.2),
    "FERTILIZER": (100, 200, "linear", 0.4, "linear", 0.4),
}
SHOPS = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL", "WOOL"),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT", "CARROT"),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}
HARVEST_AGE = {"WHEAT": 4, "CARROT": 3, "MELON": 10}
FIB = [1, 1]
for _ in range(22):
    FIB.append(FIB[-1] + FIB[-2])
_STATE = {}
MAX_WORKERS = 14
MAX_LAND = 3
LABOR_PRICE = 3.0
FUTURE_DEMAND = 0.80


def _shape(name, x, throughput):
    x = max(0.0, x)
    if name == "sqrt":
        return math.sqrt(x)
    if name == "sq":
        return x * x
    if name == "log":
        return math.log1p(x)
    if name == "log10":
        return math.log10(1.0 + x)
    if name == "hinge":
        u = x / throughput
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    return x


def _price(item, stock, overrides):
    base, throughput, below, bt, above, at = PARAMS[item]
    patch = overrides.get(item, {})
    base, throughput = patch.get("base", base), patch.get("T", throughput)
    anchor = patch.get("I0", 10000)
    if stock < anchor:
        shape = patch.get("below_func", below)
        target = patch.get("below_target", bt)
        amount = target * base * _shape(shape, anchor - stock, throughput)
        return max(1.0, base + amount / _shape(shape, throughput, throughput))
    shape = patch.get("above_func", above)
    target = patch.get("above_target", at)
    amount = target * base * _shape(shape, stock - anchor, throughput)
    return max(1.0, base - amount / _shape(shape, throughput, throughput))


def _distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _shed_tiles(size):
    h = size // 2
    return [(h - 1, h - 1), (h, h - 1), (h - 1, h), (h, h)]


def _move_actions(start, end):
    x, y = start
    a, b = end
    return [["EAST" if a > x else "WEST"]] * abs(a - x) + [
        ["SOUTH" if b > y else "NORTH"]
    ] * abs(b - y)


def _add_event(events, item, when, quantity, horizon):
    if 0 <= when <= horizon and quantity:
        events.append((item, when, float(quantity)))


def _crop_events(crop, planted, day, horizon, tile=None, fertilize=False):
    """Production that can actually be sold before the final action."""
    _, first, last, interval, cap = CROPS[crop]
    events, age = [], day - planted
    if not interval:
        target = max(age, first, min(HARVEST_AGE[crop], age + horizon))
        when = target - age
        if when > horizon:
            return events
        quantity = tile.get("yield_units", 1) if tile else 1
        window = 6 if crop == "MELON" else 2
        for a in range(max(age, window), min(target, last) + 1):
            if a == age and tile and tile.get("watered_today"):
                continue
            quantity += 1
        _add_event(events, crop, min(when + 1, horizon), min(cap, quantity), horizon)
    else:
        _add_event(
            events,
            crop,
            min(1, horizon),
            tile.get("yield_units", 0) if tile else 0,
            horizon,
        )
        covered = tile.get("fertilized_until_day", -100) - planted + 1 if tile else -100
        for a in range(first, last + 1, interval):
            if a < age or (tile and a == age):
                continue
            when = a - age
            if when <= horizon:
                if fertilize and a > covered:
                    _add_event(events, "FERTILIZER", max(0, when - 1), -1, horizon)
                    covered = a + 2
                _add_event(
                    events,
                    crop,
                    min(when + 1, horizon),
                    2 if a <= covered else 1,
                    horizon,
                )
    return events


def _animal_events(animal, placed, day, horizon, tile=None, care=True):
    _, first, interval, cap, product, _ = ANIMALS[animal]
    events, age = [], day - placed
    pending = tile.get("pending_care_bonus", 0) if tile else 0
    _add_event(
        events,
        product,
        min(1, horizon),
        tile.get("yield_units", 0) if tile else 0,
        horizon,
    )
    for d in range(horizon + 1):
        if d > 0 or (tile and tile.get("fertilizer_available")):
            _add_event(events, "FERTILIZER", min(d + 1, horizon), 1, horizon)
        if d < horizon:
            _add_event(events, "WHEAT", d, -1 if care else -0.5, horizon)
        a = age + d + 1
        if d < horizon and a >= first and (a - first) % interval == 0:
            _add_event(
                events, product, min(d + 2, horizon), min(cap, 1 + pending), horizon
            )
            pending = 0
        if care:
            pending += 1
    return events


def _forecast(obs, cfg):
    day, tpd = obs["day"], cfg.get("turnsPerDay", 24)
    horizon = max(0, (cfg.get("episodeSteps", 720) - 2) // tpd - day)
    shop_tick = tpd / cfg.get("townShopSellInterval", 4)
    center = tpd / cfg.get("townCenterSellInterval", 24)
    unlock = cfg.get("townShopUnlockInterval", 3)
    shops = obs.get("town", {}).get("unlocked_shops", [])
    known = {p: 0.0 for p in PARAMS}
    expected = {p: 0.0 for p in PARAMS}
    for products in SHOPS.values():
        for p in products:
            expected[p] += shop_tick / len(SHOPS)
    for shop in shops:
        for p in SHOPS.get(shop, ()):
            known[p] += shop_tick
    net = {p: [0.0] * (horizon + 1) for p in PARAMS}
    for d in range(1, horizon + 1):
        additions = max(0, min(8 - len(shops), (day + d) // unlock - day // unlock))
        for p in PARAMS:
            net[p][d] -= known[p] + expected[p] * additions * FUTURE_DEMAND
            if p != "FERTILIZER":
                net[p][d] -= center
    for farm in obs["farms"]:
        for row in farm["tiles"]:
            for tile in row:
                if not isinstance(tile, dict):
                    continue
                if tile.get("kind") == "PLANT":
                    crop = tile["crop"]
                    fertilize = (
                        obs["market"]["prices"][crop] * 2
                        > obs["market"]["prices"]["FERTILIZER"] * 1.3 + 12
                    )
                    events = _crop_events(
                        crop, tile["planted_day"], day, horizon, tile, fertilize
                    )
                elif tile.get("animal") in ANIMALS:
                    events = _animal_events(
                        tile["animal"], tile["placed_day"], day, horizon, tile
                    )
                else:
                    continue
                for item, d, qty in events:
                    net[item][d] += qty
    private = obs["private"]
    for p in PARAMS:
        net[p][0] += private.get("shed", {}).get(p, 0)
        net[p][min(1, horizon)] += sum(
            inv.get(p, 0) for inv in private.get("inventories", [])
        )
    stocks, overrides = {}, cfg.get("marketParams", {})
    for p in PARAMS:
        stock = obs["market"]["inventory"][p]
        stocks[p] = []
        for d in range(horizon + 1):
            change = net[p][d]
            if change > 0 and _price(p, stock + change, overrides) <= 1:
                low, high = 0.0, change
                for _ in range(12):
                    middle = (low + high) / 2
                    if _price(p, stock + middle, overrides) > 1:
                        low = middle
                    else:
                        high = middle
                change = low
            stock += change
            stocks[p].append(stock)
    return stocks, horizon


def _project(kind, day, horizon, stocks, overrides):
    if kind in CROPS:
        cost, first, last, interval, _ = CROPS[kind]
        if first > horizon:
            return None
        duration = min(horizon, last if interval else HARVEST_AGE[kind])
        fertilize = (
            bool(interval)
            and _price(kind, stocks[kind][min(horizon, first + 1)], overrides) * 2
            > _price("FERTILIZER", stocks["FERTILIZER"][max(0, first - 1)], overrides)
            * 1.3
            + 12
        )
        events = _crop_events(kind, day, day, horizon, fertilize=fertilize)
        labor = 0.7 + (2.0 if interval else 2.5) / max(1, duration)
    else:
        cost, first, _, _, _, _ = ANIMALS[kind]
        if horizon < max(5, first + 2):
            return None
        duration = horizon
        events = _animal_events(kind, day, day, horizon)
        labor = 4.1
    cumulative, revenue = {}, 0.0
    for item, d, quantity in sorted(events, key=lambda e: e[1]):
        old = cumulative.get(item, 0.0)
        value = _price(item, stocks[item][d] + old + quantity * 0.5, overrides)
        revenue += quantity * value * 0.98**d
        cumulative[item] = old + quantity
    annuity = sum(0.98**d for d in range(max(1, duration)))
    score = (revenue - cost) / annuity - LABOR_PRICE * labor
    return score, cost, events


def _apply_events(stocks, events):
    for item, when, amount in events:
        for d in range(when, len(stocks[item])):
            stocks[item][d] += amount


def _job(pos, ops, value=1000.0):
    return {"pos": pos, "ops": ops, "value": value}


def _base_jobs(obs, cfg, stocks, horizon):
    farm, day = obs["farms"][obs["player"]], obs["day"]
    prices, overrides = obs["market"]["prices"], cfg.get("marketParams", {})
    jobs, available = [], []
    for y, row in enumerate(farm["tiles"]):
        for x, tile in enumerate(row):
            pos = (x, y)
            if tile == "LOCKED":
                continue
            if (
                tile is None
                or tile.get("kind") == "WEED"
                or (tile.get("kind") in ("COOP", "PASTURE") and not tile.get("animal"))
            ):
                available.append((pos, [] if tile is None else [["DIG"]]))
                continue
            ops = []
            if tile.get("animal") in ANIMALS:
                animal = tile["animal"]
                _, first, interval, _, product, _ = ANIMALS[animal]
                future = min(horizon, max(1, first - (day - tile["placed_day"])))
                output_value = _price(product, stocks[product][future], overrides)
                care = horizon > 1 and output_value > max(5, prices["WHEAT"] * 0.55)
                feed = horizon > 0 and (care or tile.get("consecutive_unfed", 0) >= 1)
                if tile.get("yield_units", 0):
                    ops.append(["HARVEST"])
                if feed and not tile.get("fed_today"):
                    ops.append(["FEED"])
                if care and not tile.get("cared_today"):
                    ops.append(["CARE"])
                if tile.get("fertilizer_available") and prices["FERTILIZER"] > 1:
                    ops.append(["COLLECT_FERTILIZER"])
                if ops:
                    priority = (
                        4000.0
                        if feed and tile.get("consecutive_unfed", 0) >= 1
                        else 1200.0
                    )
                    jobs.append(
                        _job(
                            pos,
                            ops,
                            priority + tile.get("yield_units", 0) * prices[product],
                        )
                    )
                continue
            crop = tile["crop"]
            _, first, last, interval, cap = CROPS[crop]
            age, window = day - tile["planted_day"], 6 if crop == "MELON" else 2
            target = HARVEST_AGE.get(crop, last)
            ripe = age >= first and tile.get("yield_units", 0) > 0
            clear = not interval and ripe and (age >= target or horizon == 0)
            clear = clear or (interval and age >= last and ripe)
            if ripe and not interval and age < target:
                now_qty = min(
                    cap,
                    tile["yield_units"]
                    + (not tile.get("watered_today") and age >= window),
                )
                future_qty = min(cap, now_qty + target - age)
                ahead = min(horizon, target - age + 1)
                if (
                    prices[crop] * now_qty
                    > 1.12 * _price(crop, stocks[crop][ahead], overrides) * future_qty
                ):
                    clear = True
            water = not tile.get("watered_today") and (
                tile.get("consecutive_unwatered", 0) >= 1
                or (not interval and window <= age <= last)
            )
            fertile = False
            if interval and horizon > 0 and age < last:
                productions = [
                    a
                    for a in range(first, last + 1, interval)
                    if age < a <= min(age + 3, age + horizon)
                ]
                if productions and tile.get("fertilized_until_day", -1) < day:
                    value = sum(
                        _price(crop, stocks[crop][min(horizon, a - age + 1)], overrides)
                        for a in productions
                    )
                    fertile = (
                        value > prices["FERTILIZER"] * 1.3 + 12
                        and productions[0] == age + 1
                    )
                if (
                    productions
                    and productions[0] == age + 1
                    and (fertile or tile.get("fertilized_until_day", -1) >= day)
                ):
                    water = not tile.get("watered_today")
            elif (
                not interval
                and not tile.get("watered_today")
                and window <= age <= last
                and tile.get("fertilized_until_day", -1) < day
            ):
                remaining = max(0, min(last, age + 2, target) - age + 1)
                extra = min(
                    remaining, max(0, cap - tile.get("yield_units", 1) - remaining)
                )
                fertile = extra * prices[crop] > prices["FERTILIZER"] * 1.3 + 12
            if fertile:
                ops.append(["FERTILIZE"])
            if water and (horizon or (ripe and not interval)):
                ops.append(["WATER"])
            if ripe and (clear or interval or horizon == 0):
                ops.append(["HARVEST"])
            if clear:
                if interval:
                    ops.append(["DIG"])
                available.append((pos, ops))
            elif interval and age > last:
                available.append((pos, [["HARVEST"], ["DIG"]] if ripe else [["DIG"]]))
            elif ops:
                priority = (
                    3500.0
                    if water and tile.get("consecutive_unwatered", 0) >= 1
                    else 1500.0
                )
                jobs.append(
                    _job(pos, ops, priority + tile.get("yield_units", 0) * prices[crop])
                )
    return jobs, available


def _supplies(route):
    result = {}
    for job in route:
        for action in job["ops"]:
            item = None
            if action[0] == "FEED":
                item = "WHEAT"
            elif action[0] == "FERTILIZE":
                item = "FERTILIZER"
            elif action[0] == "PLACE":
                item = action[1]
            if item:
                result[item] = result.get(item, 0) + 1
    return result


def _route_cost(route, start, sheds, final):
    if not route:
        return 0
    cost, pos = len(_supplies(route)), start
    for job in route:
        cost += _distance(pos, job["pos"]) + len(job["ops"])
        pos = job["pos"]
    if final or any(j.get("returns") for j in route):
        cost += min(_distance(pos, shed) for shed in sheds) + 1
    return cost


def _routes(jobs, spawns, sheds, hours, final):
    routes, costs, skipped = [[] for _ in spawns], [0] * len(spawns), []
    order = sorted(
        jobs,
        key=lambda j: (
            -j["value"] // 1000,
            -min(_distance(j["pos"], p) for p in sheds),
            -len(j["ops"]),
            j["pos"],
        ),
    )
    for job in order:
        best = None
        for i, route in enumerate(routes):
            for slot in range(len(route) + 1):
                trial = route[:slot] + [job] + route[slot:]
                cost = _route_cost(trial, spawns[i], sheds, final)
                if cost <= hours:
                    candidate = (cost - costs[i] + 0.055 * cost, i, slot, cost)
                    if best is None or candidate < best:
                        best = candidate
        if best is None:
            skipped.append(job)
        else:
            _, i, slot, cost = best
            routes[i].insert(slot, job)
            costs[i] = cost
    return routes, skipped


def _plan(obs, cfg):
    farm, private, day = obs["farms"][obs["player"]], obs["private"], obs["day"]
    prices = obs["market"]["prices"]
    stocks, horizon = _forecast(obs, cfg)
    jobs, available = _base_jobs(obs, cfg, stocks, horizon)
    overrides, size = cfg.get("marketParams", {}), len(farm["tiles"])
    sheds, tpd = _shed_tiles(size), cfg.get("turnsPerDay", 24)
    remaining = min(
        tpd - obs["hour"], cfg.get("episodeSteps", 720) - 1 - obs.get("step", day * tpd)
    )
    base_inputs = _supplies(jobs)
    cash = farm["money"]
    for p in PARAMS:
        sellable = max(0, private["shed"].get(p, 0) - base_inputs.get(p, 0))
        stock = obs["market"]["inventory"][p]
        cash += (
            sum(round(_price(p, stock + n, overrides)) for n in range(sellable)) * 0.98
        )
    animal_count = sum(
        bool(isinstance(t, dict) and t.get("animal"))
        for row in farm["tiles"]
        for t in row
    )
    maintenance = sum(
        max(0, n - private["shed"].get(p, 0)) * (prices[p] * 1.1 + 1)
        for p, n in base_inputs.items()
        if p in PARAMS
    )
    reserve = maintenance + 100 + animal_count * prices["WHEAT"] * 1.25
    budget, additions, buy_land = max(0.0, cash - reserve), [], False
    if not available and horizon >= 9 and len(farm["unlocked_quadrants"]) < MAX_LAND:
        land_cost = (1000, 2000, 4000)[len(farm["unlocked_quadrants"]) - 1]
        candidates = [
            _project(k, day, horizon, stocks, overrides) for k in (*CROPS, *ANIMALS)
        ]
        best = max((c[0] for c in candidates if c), default=0)
        if (
            budget > land_cost + 1000
            and best * horizon * (size // 2) ** 2 > land_cost * 2.5
        ):
            buy_land, budget = True, budget - land_cost
            quadrant = ("NE", "SW", "SE")[len(farm["unlocked_quadrants"]) - 1]
            for y in range(size):
                for x in range(size):
                    q = ("N" if y < size // 2 else "S") + (
                        "W" if x < size // 2 else "E"
                    )
                    if q == quadrant:
                        available.append(((x, y), []))
    available.sort(key=lambda item: min(_distance(item[0], s) for s in sheds))
    for pos, prefix in available:
        best = None
        work = sum(len(j["ops"]) + 1.5 for j in jobs)
        if horizon > 0 and work < MAX_WORKERS * max(3, tpd - 6):
            for kind in (*CROPS, *ANIMALS):
                project = _project(kind, day, horizon, stocks, overrides)
                if not project:
                    continue
                score, cost, events = project
                owned = (
                    private["seeds"].get(kind, 0)
                    if kind in CROPS
                    else private["shed"].get(kind, 0)
                )
                marginal_cost = 0 if owned > additions.count(kind) else cost
                if kind in ANIMALS:
                    marginal_cost += prices["WHEAT"] * 2.5 + 5
                if marginal_cost > budget or score < 8:
                    continue
                if owned > additions.count(kind):
                    score += cost / max(3, horizon)
                if best is None or score > best[0]:
                    best = score, kind, marginal_cost, events
        if best:
            score, kind, cost, events = best
            budget -= cost
            additions.append(kind)
            _apply_events(stocks, events)
            if kind in CROPS:
                ops = prefix + [["PLANT", kind], ["WATER"]]
            else:
                ops = prefix + [
                    ["BUILD_" + ANIMALS[kind][5]],
                    ["PLACE", kind],
                    ["FEED"],
                    ["CARE"],
                ]
            jobs.append(_job(pos, ops, 1100 + max(0, score) * 2))
        elif prefix:
            jobs.append(_job(pos, prefix, 1800.0))
    output = 0
    for job in jobs:
        x, y = job["pos"]
        tile = farm["tiles"][y][x]
        if (
            isinstance(tile, dict)
            and tile.get("kind") == "PLANT"
            and ["HARVEST"] in job["ops"]
        ):
            # A ripe crop approaching decay is worth more than planting its
            # replacement; do not let the replacement lower its priority.
            job["value"] = max(
                job["value"], 5000.0 + tile.get("yield_units", 0) * prices[tile["crop"]]
            )
        job["output"] = 0
        for act in job["ops"]:
            if act[0] == "HARVEST" and isinstance(tile, dict):
                job["output"] += tile.get("yield_units", 0) + (
                    2 if ["WATER"] in job["ops"] else 0
                )
            elif act[0] == "COLLECT_FERTILIZER":
                job["output"] += 1
        output += job["output"]
    excess = output - cfg.get("shedCapacity", 100) * 0.85
    for job in sorted(
        jobs,
        key=lambda j: -j["output"] / (2 + min(_distance(j["pos"], s) for s in sheds)),
    ):
        if excess <= 0:
            break
        if job["output"]:
            job["returns"] = True
            excess -= job["output"]
    best_routes, best_loss, chosen = None, float("inf"), 1
    max_workers = min(MAX_WORKERS, max(1, len(jobs)))
    for count in range(1, max_workers + 1):
        spawns = [sheds[i % 4] for i in range(count)]
        routes, skipped = _routes(
            jobs, spawns, sheds, max(1, remaining - 3), horizon == 0
        )
        hire_cost = sum(FIB[: count - 1]) * cfg.get("farmHandCostMult", 1)
        loss = sum(j["value"] for j in skipped) + hire_cost
        if hire_cost > max(0.0, cash - maintenance) * 0.35 and count > 1:
            continue
        if loss < best_loss:
            best_loss, best_routes, chosen = loss, routes, count
        if not skipped:
            break
    if best_routes is not None:
        jobs = [job for route in best_routes for job in route]
    needed, seeds = _supplies(jobs), {}
    for j in jobs:
        for a in j["ops"]:
            if a[0] == "PLANT":
                seeds[a[1]] = seeds.get(a[1], 0) + 1
    purchases = [["BUY_LAND"]] if buy_land else []
    for item, count in needed.items():
        count -= private["shed"].get(item, 0)
        if count > 0:
            purchases.append(
                ["BUY_ANIMAL" if item in ANIMALS else "BUY_PRODUCT", item, count]
            )
    for item, count in seeds.items():
        count -= private["seeds"].get(item, 0)
        if count > 0:
            purchases.append(["BUY_SEED", item, count])
    return {
        "day": day,
        "jobs": jobs,
        "needed": needed,
        "purchases": purchases,
        "workers": chosen,
        "routes": None,
        "stage": 0,
        "horizon": horizon,
        "skipped": 0,
        "last_step": obs.get("step", 0) - 1,
    }


def _prepare_routes(plan, obs, cfg):
    farm, private = obs["farms"][obs["player"]], obs["private"]
    spawns = [tuple(farm["farmer"])] + [tuple(p) for p in farm["hands"]]
    sheds = _shed_tiles(len(farm["tiles"]))
    hours = min(
        cfg.get("turnsPerDay", 24) - obs["hour"],
        cfg.get("episodeSteps", 720) - 1 - obs["step"],
    )
    supply, seeds, jobs = dict(private["shed"]), dict(private["seeds"]), []
    for job in plan["jobs"]:
        ops = []
        for action in job["ops"]:
            op = action[0]
            if op == "PLANT":
                if seeds.get(action[1], 0) <= 0:
                    break
                seeds[action[1]] -= 1
            if op == "PLACE":
                if supply.get(action[1], 0) <= 0:
                    if ops and ops[-1][0].startswith("BUILD_"):
                        ops.pop()
                    break
                supply[action[1]] -= 1
            if op in ("FEED", "FERTILIZE"):
                item = "WHEAT" if op == "FEED" else "FERTILIZER"
                if supply.get(item, 0) <= 0:
                    continue
                supply[item] -= 1
            ops.append(action)
        if ops:
            jobs.append({**job, "ops": ops})
    routes, skipped = _routes(jobs, spawns, sheds, hours, plan["horizon"] == 0)
    plan["skipped"] = len(skipped)
    sequences = []
    for i, route in enumerate(routes):
        sequence = [["PICKUP", item, n] for item, n in _supplies(route).items()]
        pos = spawns[i]
        for job in route:
            sequence.extend(_move_actions(pos, job["pos"]))
            sequence.extend(job["ops"])
            pos = job["pos"]
        if route and (plan["horizon"] == 0 or any(j.get("returns") for j in route)):
            end = min(sheds, key=lambda s: _distance(pos, s))
            if len(sequence) + _distance(pos, end) + 1 <= hours:
                sequence.extend(_move_actions(pos, end))
                sequence.append(["DROP"])
        sequences.append(sequence)
    plan["routes"] = sequences


def agent(obs, configuration=None):
    """Kaggle entry point. No network, engine imports, or external assets."""
    cfg, player = configuration or {}, obs.get("player", 0)
    if not obs.get("farms") or player >= len(obs["farms"]):
        return {"farmer": ["PASS"], "hands": [], "market": []}
    farm, private = obs["farms"][player], obs["private"]
    step = obs.get("step", obs["day"] * cfg.get("turnsPerDay", 24) + obs["hour"])
    plan = _STATE.get(player)
    if plan is None or plan["day"] != obs["day"] or step <= plan["last_step"]:
        plan = _plan(obs, cfg)
        _STATE[player] = plan
    plan["last_step"] = step
    limit, market = cfg.get("maxMarketOrdersPerTurn", 10), []
    actions = [["PASS"] for _ in range(1 + len(farm["hands"]))]
    if plan["routes"] is None:
        for item in PARAMS:
            n = private["shed"].get(item, 0) - plan["needed"].get(item, 0)
            if n > 0 and len(market) < limit:
                market.append(["SELL", item, n])
        while plan["purchases"] and len(market) < limit:
            market.append(plan["purchases"].pop(0))
        missing = max(0, plan["workers"] - len(actions))
        for _ in range(min(missing, limit - len(market))):
            market.append(["HIRE"])
        if not market or (
            not plan["purchases"]
            and plan["stage"] > 0
            and (not missing or plan["stage"] >= 3)
        ):
            _prepare_routes(plan, obs, cfg)
        plan["stage"] += 1
    if plan["routes"] is not None:
        for i, route in enumerate(plan["routes"]):
            if i < len(actions) and route:
                actions[i] = route.pop(0)
        reserved = {}
        for route in plan["routes"]:
            for a in route:
                if a[0] == "PICKUP":
                    reserved[a[1]] = reserved.get(a[1], 0) + a[2]
        for item in PARAMS:
            n = private["shed"].get(item, 0) - reserved.get(item, 0)
            for i, action in enumerate(actions):
                inv = (
                    private["inventories"][i] if i < len(private["inventories"]) else {}
                )
                if action[0] == "PICKUP" and action[1] == item:
                    n -= action[2]
                elif action[0] == "DROP":
                    n += inv.get(item, 0)
            if n > 0 and len(market) < limit:
                market.append(["SELL", item, n])
    return {"farmer": actions[0], "hands": actions[1:], "market": market[:limit]}
