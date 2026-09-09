# Kaggriculture rules reference

Current competition rules and enrolment are published on the [Kaggriculture overview](https://www.kaggle.com/competitions/kaggriculture/overview). This local reference records the agent contract used by this repository; when it conflicts with the competition environment, the competition environment wins.

## Objective and season

Two players manage separate farms for a 30-day, 24-turn-per-day season (720 turns by default). The winner has the most bank coins. Farms are public, while each player's shed, seeds, and carried inventories are private.

Each player starts with the NW 5×5 quadrant unlocked. NE, SW, and SE land can be bought for $1k, $2k, and $4k. The farmer and hired hands take one field action each turn; market orders are ordered and capped at `maxMarketOrdersPerTurn` (10 by default).

## Agent interface

An agent accepts `obs` (and may accept `configuration`) and returns:

```python
{
    "farmer": [op, ...args],
    "hands": [[op, ...args], ...],
    "market": [[op, ...args], ...],
}
```

`hands` must contain exactly one action for every current hired hand. The farmer and hands may move with `NORTH`, `SOUTH`, `EAST`, `WEST`, or `PASS`; perform shed actions (`PICKUP`, `PLACE`, `DROP`); manage crops (`PLANT`, `WATER`, `HARVEST`, `FERTILIZE`); manage animals (`BUILD_COOP`, `BUILD_PASTURE`, `FEED`, `CARE`, `COLLECT_FERTILIZER`); or clear terrain with `DIG`.

Market actions are `BUY_SEED`, `BUY_PRODUCT`, `BUY_ANIMAL`, `SELL`, `HIRE`, and `BUY_LAND`. Invalid actions silently no-op.

## Critical gameplay constraints

- Plants need daily water and animals need daily wheat feed. Two consecutive missed end-of-day refreshes create weeds or make animals escape permanently; planting day already counts as unwatered.
- The shed holds at most 100 non-seed items. Overflow at end-of-day is discarded. Seeds have their own uncapped storage and are consumed directly by `PLANT`.
- A unit accesses the shed only from the four central adjacent tiles. `PLACE` can put matching animals on matching empty structures, or move an item into the shed.
- Crop yields depend on crop age and watering; fertilizer boosts the applicable yield window. Animals produce indefinitely while fed, with a cap only on unharvested tile output.
- Sale prices are dynamic with shared market inventory. Town demand changes over the season, so agents must use the observation rather than assume a fixed price.

## Observation fields used by this repo

`player`, `step`, `day`, and `hour` identify the turn. `farms[player]` provides money, board tiles, unit positions, unlocked quadrants, and hire count. `private` provides this player's shed, seeds, and per-unit inventories. `market` provides inventory and prices; `town` provides active shops.

See the competition environment for complete crop, animal, shop, price, and configuration tables.
