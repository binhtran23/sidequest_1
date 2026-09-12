# SPDX-License-Identifier: Apache-2.0
"""Experimental strategy switches over an independently loaded champion.

Development only. Sources and hashes are recorded in the slice manifest.
No Kaggle replay, opponent private inventory, or future observation is read.
"""
import copy
import importlib.util
import uuid
from collections import Counter
from pathlib import Path

SLICE = Path(__file__).resolve().parents[2]
ASTRA = SLICE.parent / "astra-current/base/main.py"
MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}


def load(path):
    spec = importlib.util.spec_from_file_location("test_policy_" + uuid.uuid4().hex, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestPolicy:
    def __init__(self, settings):
        self.settings = settings
        self.router = load(SLICE / "base/router.py")
        self.astra = load(ASTRA)
        self.events = []
        self.players = {}
        self.context = None
        r = self.router
        r.SALE_HORIZON = settings.get("sale_horizon", 2)
        self.native_reserve = r.reserve_sales
        self.native_qualifies = r._v219_qualifies
        if settings.get("sale_pressure"):
            r.reserve_sales = self.reserve_sales
        elif r.SALE_HORIZON != 2:
            r.reserve_sales = self.apply_native_reserve
        if settings.get("tomato_gate") or settings.get("tomato_off"):
            r._v219_qualifies = self.tomato_qualifies

    def emit(self, hypothesis, **fields):
        obs, _ = self.context
        self.events.append({"type": "strategy_decision", "hypothesis": hypothesis,
                            "turn": int(obs["step"]), "player": int(obs["player"]), **fields})

    def drain(self):
        events, self.events = self.events, []
        return events

    def apply_native_reserve(self, action, view, state, tape, step):
        before = len(action["market"])
        self.native_reserve(action, view, state, tape, step)
        if self.router.SALE_HORIZON != 2:
            for order in action["market"][before:]:
                self.emit("sale_horizon", horizon=self.router.SALE_HORIZON, item=order[1], quantity=order[2])

    def reserve_sales(self, action, view, state, tape, step):
        """Extend the native debt-aware window only under visible supply pressure."""
        obs, cfg = self.context
        self.apply_native_reserve(action, view, state, tape, step)
        stock = self.router.projected_shed(action, view)
        end = min(718, step + 12, (step // 72 + 1) * 72 - 1)
        market = action["market"]
        blocked = {o[1] for o in market if len(o) > 1}
        commands = [action["farmer"], *action["hands"]]
        blocked.update(c[1] for c in commands if len(c) > 1 and c[0] == "PICKUP")
        blocked.update(c[1] for q in state.queues.values() for c in q
                       if len(c) > 1 and c[0] == "PICKUP")
        if any(c[0] == "PLACE" and len(c) > 1 and c[1] in self.router.ANIMALS
               and view.inventory(i).get(c[1], 0) for i, c in enumerate(commands)):
            return
        opponent = obs["farms"][1-obs["player"]]
        visible = Counter()
        for row in opponent["tiles"]:
            for tile in row:
                if isinstance(tile, dict):
                    item = tile.get("crop") or {"COW": "MILK", "SHEEP": "WOOL", "GOOSE": "EGG"}.get(tile.get("animal"))
                    if item:
                        # A supply proxy, not an inference of private inventory.
                        visible[item] += max(1, tile.get("yield_units", 0))
        for item in self.router.PRODUCTS:
            if item in blocked or item in ("WHEAT", "FERTILIZER") or stock.get(item, 0) <= 0:
                continue
            if len(market) >= cfg.get("maxMarketOrdersPerTurn", 10):
                break
            due = None
            for t in range(step+1, end+1):
                future = tape[t]
                work = [future["farmer"], *future["hands"]]
                if any(c[:2] == ["PICKUP", item] for c in work):
                    break
                if any(o[:2] == ["BUY_PRODUCT", item] for o in future["market"]):
                    break
                planned = sum(int(o[2]) for o in future["market"] if o[:2] == ["SELL", item])
                planned -= getattr(state, "sale_window_debts", {}).get(t, {}).get(item, 0)
                if planned > 0:
                    due = (t, min(planned, stock[item]))
                    break
            if due is None or visible[item] == 0:
                continue
            t, quantity = due
            demand = sum(self.astra.SHOPS.get(shop, ()).count(item)
                         for shop in obs["town"]["unlocked_shops"])
            ticks = sum(k % cfg.get("townShopSellInterval", 4) == 0 for k in range(step, t))
            town = sum(k % cfg.get("townCenterSellInterval", 24) == 0 for k in range(step, t))
            inventory = obs["market"]["inventory"][item]
            pressure = min(quantity, visible[item])
            future_stock = inventory - demand * ticks - town + pressure
            overrides = cfg.get("marketParams", {})
            now = sum(round(self.astra._price(item, inventory+n, overrides)) for n in range(quantity))
            later = sum(round(self.astra._price(item, future_stock+n, overrides)) for n in range(quantity))
            if now <= later or view.prices[item] <= 1:
                continue
            market.append(["SELL", item, quantity])
            debts = getattr(state, "sale_window_debts", {})
            debt = debts.setdefault(t, {})
            debt[item] = debt.get(item, 0) + quantity
            state.sale_window_debts = debts
            self.emit("sale_timing", item=item, quantity=quantity, original_turn=t,
                      estimated_now=now, estimated_later=later)

    def tomato_qualifies(self, obs, native):
        eligible = self.native_qualifies(obs, native)
        if not eligible:
            return False
        if self.settings.get("tomato_off"):
            self.emit("tomato_gate", accept=False, reason="investment_disabled_ablation")
            return False
        _, cfg = self.context
        stocks, horizon = self.astra._forecast(obs, cfg)
        price = lambda item, d: self.astra._price(item, stocks[item][min(d, horizon)], cfg.get("marketParams", {}))
        wages = 0
        for day in range(18, 30):
            tape = self.router._v219_native_day(native, day)
            hands = max(len(a["hands"]) for a in tape)
            count = 1 if day in (19, 20, 21, 22, 23, 25) else (3 if day in (26, 27, 28) else 2)
            count += int(day == 27 and price("FERTILIZER", 9) <= 30)
            wages += sum(self.router._v219_fib(i) for i in range(hands, hands+count))
        revenue = sum(10 * (2 if price("FERTILIZER", 6 if day == 26 else 9) <= 30 else 1)
                      * price("TOMATO", day-18) for day in range(26, 30))
        fertilizer = sum(10 * max(1, price("FERTILIZER", d)) for d in (6, 9) if price("FERTILIZER", d) <= 30)
        cost = 4500 + wages + fertilizer
        accept = revenue > 1.15 * cost
        self.emit("tomato_gate", accept=accept, forecast_revenue=round(revenue, 2),
                  estimated_cost=round(cost, 2), extra_wages=wages)
        return accept

    def feed_supply(self, obs, action):
        """Buy the next known pickup shortfall after accounting for this market."""
        step = obs["step"]
        if not 24 <= step < 696 or step % 24 == 23 or (step+1) % 72 == 0:
            return
        if len(action["market"]) >= 10:
            return
        r = self.router
        state = r._POLICY.players[obs["player"]]
        view = r.FarmView(obs)
        work = [action["farmer"], *action["hands"]]
        nxt = r._POLICY.tapes[state.plan][step+1]
        future = [nxt["farmer"], *nxt["hands"]]
        demand = 0
        for i, position in enumerate(view.positions):
            x, y = position
            if work[i][0] in MOVES:
                dx, dy = MOVES[work[i][0]]
                x, y = max(0, min(9, x+dx)), max(0, min(9, y+dy))
            if not view.beside_shed((x, y)):
                continue
            queue = state.queues.get(i)
            cmd = queue[0] if queue else (future[i] if i < len(future) else ["PASS"])
            if cmd[:2] == ["PICKUP", "WHEAT"]:
                demand += int(cmd[2]) if len(cmd) > 2 else 1
        stock = r.projected_shed(action, view)
        farm = obs["farms"][obs["player"]]
        budget = farm["money"]
        hires = farm["hires_today"]
        for order in action["market"]:
            if not order:
                continue
            op = order[0]
            if op == "SELL":
                stock[order[1]] = max(0, stock.get(order[1], 0)-int(order[2]))
            elif op in ("BUY_PRODUCT", "BUY_ANIMAL", "BUY_SEED"):
                item, qty = order[1], int(order[2])
                price = ({"COW":400,"SHEEP":500,"GOOSE":300}[item] if op == "BUY_ANIMAL"
                         else self.astra.CROPS[item][0] if op == "BUY_SEED" else obs["market"]["prices"][item]+10)
                budget -= qty * price
                if op != "BUY_SEED":
                    stock[item] = stock.get(item, 0)+qty
            elif op == "HIRE":
                budget -= r._v219_fib(hires)
                hires += 1
            elif op == "BUY_LAND":
                budget -= (1000, 2000, 4000)[min(2, len(farm["unlocked_quadrants"])-1)]
        shortage = max(0, demand-stock.get("WHEAT", 0))
        if 0 < shortage <= 8 and sum(stock.values())+shortage <= 100:
            if budget >= 150 + shortage*(obs["market"]["prices"]["WHEAT"]+10):
                action["market"].append(["BUY_PRODUCT", "WHEAT", shortage])
                self.emit("feed_reservation", quantity=shortage, next_pickup_demand=demand)

    def crop_choice(self, obs, action, state):
        """Swap only late carrot sowings for wheat on the same worker trajectory."""
        if obs["step"] == 528:
            stocks, horizon = self.astra._forecast(obs, self.context[1])
            # Both mature at age two; the existing carrot route harvests by age
            # three. Compare wheat's three units with carrot's four, not wheat's
            # longer full-yield schedule. Re-evaluate no unknown future state.
            prices = {p: self.astra._price(p, stocks[p][min(4, horizon)], self.context[1].get("marketParams", {}))
                      for p in ("WHEAT", "CARROT")}
            wheat, carrot = 3*prices["WHEAT"]-10, 4*prices["CARROT"]-20
            state["wheat_crop"] = wheat > 1.15*carrot
            self.emit("crop_choice", wheat_branch=state["wheat_crop"], wheat_value=wheat, carrot_value=carrot)
        if not state.get("wheat_crop"):
            return
        for order in action["market"]:
            if order[:2] == ["BUY_SEED", "CARROT"]:
                order[1] = "WHEAT"
                self.emit("crop_seed", quantity=order[2])
        commands = [action["farmer"], *action["hands"]]
        wheat_seeds = obs["private"]["seeds"].get("WHEAT", 0)
        wheat_seeds -= sum(c == ["PLANT", "WHEAT"] for c in commands)
        for i, cmd in enumerate(commands):
            if cmd == ["PLANT", "CARROT"] and wheat_seeds > 0:
                commands[i] = ["PLANT", "WHEAT"]
                wheat_seeds -= 1
                self.emit("crop_plant", unit=i)
        action["farmer"], action["hands"] = commands[0], commands[1:]
        # Existing scheduled carrot sales now liquidate the substitute harvest.
        # Keep original sales for any carrot planted before the branch.
        projected = self.router.projected_shed(action, self.router.FarmView(obs))
        for order in action["market"]:
            if order[:2] == ["SELL", "CARROT"] and projected.get("CARROT", 0) == 0:
                quantity = min(projected.get("WHEAT", 0), max(0, int(order[2])*3//4))
                if quantity:
                    order[1], order[2] = "WHEAT", quantity
                    projected["WHEAT"] -= quantity

    def endgame(self, obs, action, state):
        """Use Astra greedy insertion for harvest-and-delivery jobs on day 29."""
        if obs["step"] < 698:
            return
        r, a = self.router, self.astra
        farm = obs["farms"][obs["player"]]
        positions = [tuple(farm["farmer"]), *map(tuple, farm["hands"])]
        sheds = a._shed_tiles(10)
        if "final_routes" not in state:
            jobs = []
            for y, row in enumerate(farm["tiles"]):
                for x, tile in enumerate(row):
                    if not isinstance(tile, dict) or tile.get("yield_units", 0) <= 0:
                        continue
                    item = tile.get("crop") or {"COW":"MILK","SHEEP":"WOOL","GOOSE":"EGG"}.get(tile.get("animal"))
                    if not item:
                        continue
                    if tile.get("crop") and obs["day"]-tile["planted_day"] < a.CROPS[item][1]:
                        continue
                    ops, qty = [], tile["yield_units"]
                    if item in ("CARROT", "WHEAT", "MELON") and not tile.get("watered_today"):
                        ops.append(["WATER"])
                        qty = min(a.CROPS[item][4], qty+1)
                    ops.append(["HARVEST"])
                    jobs.append({"pos": (x,y), "ops": ops, "value": qty*obs["market"]["prices"][item]*1000,
                                 "returns": True, "output": qty})
            hours = 719-obs["step"]
            routes, skipped = a._routes(jobs, positions, sheds, hours, True)
            sequences = []
            for i, route in enumerate(routes):
                seq, pos = [], positions[i]
                for job in route:
                    seq.extend(a._move_actions(pos, job["pos"]))
                    seq.extend(job["ops"])
                    pos = job["pos"]
                if route or any(obs["private"]["inventories"][i].values()):
                    home = min(sheds, key=lambda p: a._distance(pos, p))
                    seq.extend(a._move_actions(pos, home))
                    seq.append(["DROP"])
                sequences.append(seq)
            state["final_routes"] = sequences
            self.emit("endgame_plan", jobs=len(jobs), skipped=len(skipped), workers=len(sequences), hours=hours)
        commands = [seq.pop(0) if seq else ["PASS"] for seq in state["final_routes"]]
        action["farmer"], action["hands"] = commands[0], commands[1:]
        stock = r.projected_shed(action, r.FarmView(obs))
        action["market"] = [["SELL", p, stock.get(p, 0)] for p in r.PRODUCTS if stock.get(p, 0)>0]
        action["market"].sort(key=lambda o: -o[2]*obs["market"]["prices"][o[1]])
        self.emit("endgame_actions", actions=commands, market=action["market"])

    def agent(self, obs, configuration=None):
        cfg = configuration or {}
        self.context = obs, cfg
        player = int(obs["player"])
        state = self.players.get(player)
        if state is None or obs["step"] <= state["step"]:
            state = self.players[player] = {"step": -1}
        state["step"] = obs["step"]
        action = self.router.agent(obs, cfg)
        if self.settings.get("feed_reservation"):
            self.feed_supply(obs, action)
        if self.settings.get("crop_choice"):
            self.crop_choice(obs, action, state)
        if self.settings.get("endgame"):
            self.endgame(obs, action, state)
        return action
