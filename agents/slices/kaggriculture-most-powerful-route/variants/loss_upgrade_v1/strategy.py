# SPDX-License-Identifier: Apache-2.0
"""Append-only policy source for the frozen champion; standard library only.

This is an independent strategy layer, not the restricted adaptive wrapper.
The build tool embeds it after the audited champion to make main.py standalone.
"""

_LOSS_SETTINGS = {"fertilizer": "window", "sale_horizon": 4, "sale_pressure": True, "late_harvest": False}
_LOSS_CROPS = {"WHEAT": (2,4,0,6), "CARROT": (2,3,0,4),
               "MELON": (10,12,0,6), "TOMATO": (8,8,1,4), "STRAWBERRY": (10,10,2,4)}
_LOSS_EVENTS = []
_LOSS_PARENT = agent
_LOSS_PARENT_DRAIN = drain_telemetry
_LOSS_NATIVE_RESERVE = reserve_sales
_LOSS_OBSERVATION = None


def reserve_sales(action, view, state, tape, step):
    """Extend the window only for goods facing visible competing production."""
    global SALE_HORIZON
    if not _LOSS_SETTINGS.get('sale_pressure') or _LOSS_OBSERVATION is None:
        return _LOSS_NATIVE_RESERVE(action, view, state, tape, step)
    SALE_HORIZON = 3
    _LOSS_NATIVE_RESERVE(action, view, state, tape, step)
    end = min(LAST_STEP, (step//72+1)*72-1)
    if step < 144 or step+4 > end or len(action['market']) >= MAX_ORDERS:
        return
    planned = {o[1] for o in tape[step+4]['market'] if len(o)>=3 and o[0]=='SELL'}
    planned.difference_update(('WHEAT','FERTILIZER'))
    planned.difference_update(o[1] for o in action['market'] if len(o)>1 and o[0] in ('SELL','BUY_PRODUCT'))
    # The native pass has already projected this turn's field actions. Its
    # market additions do not change that projection. A fourth-turn sale is
    # impossible without projected stock, so skip the rival scan in that case.
    stock = getattr(view, '_sale_stock', {})
    planned = {item for item in planned if stock.get(item,0)>0}
    if not planned:
        return
    obs = _LOSS_OBSERVATION
    threatened = set()
    for row in obs['farms'][1-obs['player']]['tiles']:
        for tile in row:
            if isinstance(tile,dict) and tile.get('yield_units',0)>0:
                item = tile.get('crop') or {'COW':'MILK','SHEEP':'WOOL','GOOSE':'EGG'}.get(tile.get('animal'))
                if item in planned:
                    threatened.add(item)
    if not threatened:
        return
    prices = view.prices
    view.prices = {p:v if p in threatened else 0 for p,v in prices.items()}
    SALE_HORIZON = 4
    start = len(_SUBMISSION_SALE_EVENTS)
    try:
        _LOSS_NATIVE_RESERVE(action,view,state,tape,step)
        for event in _SUBMISSION_SALE_EVENTS[start:]:
            event['horizon'] = 4
            event['reason'] = 'visible_competing_production'
    finally:
        view.prices = prices
        SALE_HORIZON = 3


def _loss_bonus_days(tile, day):
    first, maximum, interval, cap = _LOSS_CROPS[tile['crop']]
    days = []
    for d in range(day, min(day + 3, 30)):
        if tile.get('fertilized_until_day', -1) >= d:
            continue
        age = d - tile['planted_day']
        if interval:
            offset = age + 1 - first
            eligible = offset >= 0 and offset % interval == 0 and offset // interval < cap
        else:
            eligible = ((maximum + 1) // 2 <= age <= maximum
                        and tile.get('yield_units', 0) < cap
                        and (d != day or not tile.get('watered_today')))
        if eligible:
            days.append(d)
    return days


def _loss_emit(obs, hypothesis, **fields):
    _LOSS_EVENTS.append({'type': 'strategy_decision', 'turn': obs['step'],
                         'hypothesis': hypothesis, **fields})


def _loss_field_actions(obs, action):
    """Reallocate only stationary idle/no-op work; positions remain compatible."""
    mode = _LOSS_SETTINGS.get('fertilizer', 'none')
    late = _LOSS_SETTINGS.get('late_harvest', False)
    day, step = int(obs['day']), int(obs['step'])
    if step >= LAST_STEP or (mode == 'none' and not late):
        return
    if mode in ('legacy','window') and day < 18 and not late:
        return
    farm = obs['farms'][obs['player']]
    private = obs['private']
    positions = [farm['farmer'], *farm['hands']]
    commands = [action['farmer'], *action['hands']]
    claimed = set()
    for unit, (position, cmd) in enumerate(zip(positions, commands)):
        if cmd[0] not in ('PASS','WATER'):
            if cmd[0] not in ('NORTH','SOUTH','EAST','WEST','DROP','PICKUP','PLACE'):
                claimed.add(tuple(position))
            continue
        x,y = position
        tile = farm['tiles'][y][x]
        inv = private['inventories'][unit]
        if not isinstance(tile, dict) or tuple(position) in claimed:
            continue
        crop = tile.get('crop')
        # A repeated WATER is provably idle only if no earlier actor mutates
        # this tile; claim all earlier tile work below to avoid stale state.
        idle = cmd == ['PASS'] or (cmd == ['WATER'] and tile.get('watered_today'))
        if mode == 'legacy':
            if (day >= 18 and cmd == ['PASS'] and crop and inv.get('FERTILIZER', 0)
                    and tile.get('fertilized_until_day', -1) < day + 2):
                commands[unit] = ['FERTILIZE']
                _loss_emit(obs, 'fertilizer_legacy', unit=unit, crop=crop)
        elif mode == 'window' and idle and crop and inv.get('FERTILIZER', 0):
            days = _loss_bonus_days(tile, day)
            # Do not withhold fertilizer cash during the fragile hiring opening.
            # Require a new bonus window within the three active days.
            watered = tile.get('watered_today')
            expected = min(len(days), _LOSS_CROPS[crop][3]-tile.get('yield_units',0)) * obs['market']['prices'].get(crop,0)
            cost = obs['market']['prices'].get('FERTILIZER',0)
            native = _POLICY.players[obs['player']]
            end = min(LAST_STEP, (step//24+1)*24-1)
            reserved = sum(1 for t in range(step+1,end+1)
                           if ([_POLICY.tapes[native.plan][t]['farmer'], *_POLICY.tapes[native.plan][t]['hands']] + [['PASS']]*(unit+1))[unit] == ['FERTILIZE'])
            if day >= 18 and days and watered and expected > cost and inv['FERTILIZER'] > reserved:
                commands[unit] = ['FERTILIZE']
                _loss_emit(obs, 'fertilizer_window', unit=unit, crop=crop,
                           expected_bonus_value=expected, fertilizer_sale_value=cost,
                           potential_days=days, reserved_units=reserved)
            else:
                _loss_emit(obs, 'fertilizer_rejected', unit=unit, crop=crop,
                           reason='opening_or_window_or_value_or_reservation', potential_days=days,
                           expected_bonus_value=expected, fertilizer_sale_value=cost)
        if late and day >= 27 and idle and commands[unit] == cmd and tile.get('yield_units',0) > 0:
            mature = not crop or day - tile['planted_day'] >= _LOSS_CROPS[crop][0]
            # Only take output at the shed; the inherited final turn can deliver
            # it even if no intervening tape DROP was scheduled.
            center = len(farm['tiles'])//2
            at_shed = x in (center-1,center) and y in (center-1,center)
            # Do not alter one-shot crop continuations before the final day.
            safe_crop = not crop or _LOSS_CROPS[crop][2] > 0 or day == 29
            load = sum(private['shed'].values()) + sum(sum(i.values()) for i in private['inventories'])
            if mature and at_shed and safe_crop and load + tile['yield_units'] <= 100:
                commands[unit] = ['HARVEST']
                _loss_emit(obs, 'late_harvest', unit=unit, quantity=tile['yield_units'],
                           expected_sale_value=tile['yield_units']*obs['market']['prices'].get(crop or {'COW':'MILK','SHEEP':'WOOL','GOOSE':'EGG'}.get(tile.get('animal')),0))
        if commands[unit][0] not in ('PASS','NORTH','SOUTH','EAST','WEST','DROP','PICKUP','PLACE'):
            claimed.add(tuple(position))
    action['farmer'], action['hands'] = commands[0],commands[1:]


def agent(observation, configuration=None):
    global SALE_HORIZON, _LOSS_OBSERVATION
    _LOSS_OBSERVATION = observation
    SALE_HORIZON = int(_LOSS_SETTINGS.get('sale_horizon', 3))
    action = _LOSS_PARENT(observation, configuration)
    _loss_field_actions(observation, action)
    return action


def drain_telemetry():
    events = _LOSS_PARENT_DRAIN()
    for event in events:
        if event.get('hypothesis') == 'sale_horizon' and not _LOSS_SETTINGS.get('sale_pressure'):
            event['horizon'] = SALE_HORIZON
    events.extend(_LOSS_EVENTS)
    _LOSS_EVENTS.clear()
    return events


# Last inserted callable for Kaggle's source loader.
_LOSS_KAGGLE_ENTRYPOINT = agent
