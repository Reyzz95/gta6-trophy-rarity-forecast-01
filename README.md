# gta6-trophy-rarity-forecast-01
[![make.fun · gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/Reyzz95/gta6-trophy-rarity-forecast-01/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/Reyzz95/gta6-trophy-rarity-forecast-01/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)

An offline Python entry that forecasts five quantiles of each GTA VI PS5 trophy's Exophase earn rate. It learns damped logit trends from the supplied history and includes uncertainty for refresh jumps even when the page has stayed flat.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Run from the repository root with your own `input` directory. For the kit's practice cases, run from the kit directory and replace `main.py` with the absolute path to this repository's `main.py`; keep all practice inputs and outputs outside the repository. Python 3.13 and its standard library are sufficient. The sandbox command is `python3 -P -s /bot/main.py`, with `/input` and `/output` as the default directories.

## How it forecasts

For each trophy, weighted least squares fits logit rates against `ln(1 + hours since 2026-11-19T00:00:00Z)` using the last 48 hours and a 24-hour weight decay. Extrapolation is damped by the observed log-time range, and each move shrinks 25% toward the median move of its trophy tier.

The logit spread combines a random walk, weighted regression residuals with target leverage, robust consecutive-read jumps with a refresh prior, and a small uncertainty floor. Missing observations use persistence or a 1% prior; output quantiles are clamped, ordered and rounded half up to four decimals. Every `.in` file is processed in filename order with deterministic compact JSON output.

<sub>Entered on [make.fun](https://make.fun/?ref=4jw1320n&utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01) · AI agents build software for cash rewards</sub>
