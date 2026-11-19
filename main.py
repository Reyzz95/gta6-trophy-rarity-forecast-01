"""Offline trophy forecasts using damped, recency-weighted logit trends.

Fit logit rates against log(1 + hours since launch) over the last 48 hours,
with a 24-hour exponential weight decay. Damp extrapolation by the observed
log-time range, then shrink moves 25% toward their trophy tier's median.
Combine random-walk, weighted-fit, refresh-jump and floor uncertainties;
emit five clamped normal-logit quantiles with positive half-up rounding.
No learned parameters, external dependencies, network or model calls are used.
"""

import json
import math
import os
from pathlib import Path


NORMAL_SCORES = (-1.645, -0.674, 0.0, 0.674, 1.645)


def utc_hours(stamp):
    """Parse an ISO UTC timestamp into hours on a Gregorian calendar."""
    year, month, day = (int(part) for part in stamp[:10].split("-"))
    previous = year - 1
    days = 365 * previous + previous // 4 - previous // 100 + previous // 400
    month_days = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    days += sum(month_days[:month - 1]) + day - 1
    if month > 2 and year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        days += 1
    clock = stamp[11:].removesuffix("Z").removesuffix("+00:00")
    hour, minute, second = clock.split(":")
    return days * 24 + int(hour) + int(minute) / 60 + float(second) / 3600


LAUNCH_HOUR = utc_hours("2026-11-19T00:00:00Z")


def log_time(hour):
    # Preserve the kit's pre-midnight read; guard much earlier observations.
    return math.log1p(max(hour - LAUNCH_HOUR, -1.0 + 1e-12))


def rate_logit(rate):
    bounded = min(max(float(rate), 0.01), 99.99)
    return math.log(bounded / (100.0 - bounded))


def middle(values):
    ordered = sorted(values)
    count = len(ordered)
    if count % 2:
        return ordered[count // 2]
    return (ordered[count // 2 - 1] + ordered[count // 2]) / 2.0


def percent(value):
    """Stable inverse logit even for extreme fitted trends."""
    if value >= 0:
        return 100.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return 100.0 * exp_value / (1.0 + exp_value)


def rounded_rate(value):
    return math.floor(value * 10000.0 + 0.5) / 10000.0


def fit_trend(samples, checkpoint, target_x):
    """Return damped move and prediction std, or persistence and 0.6."""
    if len(samples) < 3 or len({sample[1] for sample in samples}) < 3:
        return 0.0, 0.6
    x_range = max(row[1] for row in samples) - min(row[1] for row in samples)
    if x_range <= 0:
        return 0.0, 0.6
    # Constant pages have an exactly flat fit. Avoid cancellation noise in
    # weighted means (observed in practice) and unnecessary regression work.
    if all(row[2] == samples[0][2] for row in samples):
        return 0.0, 0.0
    weights = [math.exp(-max(0.0, checkpoint - row[0]) / 24.0)
               for row in samples]
    weight_sum = math.fsum(weights)
    x_bar = math.fsum(w * row[1] for w, row in zip(weights, samples)) / weight_sum
    y_bar = math.fsum(w * row[2] for w, row in zip(weights, samples)) / weight_sum
    xx = math.fsum(w * (row[1] - x_bar) ** 2
                   for w, row in zip(weights, samples))
    if xx <= 0:
        return 0.0, 0.6
    xy = math.fsum(w * (row[1] - x_bar) * (row[2] - y_bar)
                   for w, row in zip(weights, samples))
    slope = xy / xx
    prediction = y_bar + slope * (target_x - x_bar)
    last_x, last_y = samples[-1][1:]
    extrapolation = max(0.0, target_x - last_x)
    move = x_range / (x_range + extrapolation) * (prediction - last_y)
    variance = math.fsum(w * (row[2] - y_bar - slope * (row[1] - x_bar)) ** 2
                         for w, row in zip(weights, samples)) / weight_sum
    leverage = 1.0 / len(samples) + (target_x - x_bar) ** 2 / xx
    return move, math.sqrt(max(0.0, variance) * (1.0 + leverage))


def forecast(case):
    checkpoint = utc_hours(case["at"])
    target_x = log_time(utc_hours(case["target"]))
    horizon_hours = max(0.0, float(case["horizon_minutes"]) / 60.0)
    rw_variance = 0.25 * (horizon_hours / 24.0)
    refreshes = max(1.0, horizon_hours / 6.0)
    history = [(utc_hours(read["at"]), read["rates"])
               for read in case["history"]]
    estimates = []
    tier_moves = {}
    for index, trophy in enumerate(case["trophies"]):
        usable = [(hour, log_time(hour), rate_logit(rates[index]))
                  for hour, rates in history
                  if index < len(rates) and rates[index] is not None]
        last_y = usable[-1][2] if usable else rate_logit(1.0)
        window = [row for row in usable if row[0] >= checkpoint - 48.0]
        if not window:
            move, spread = 0.0, 2.0
        else:
            move, fit_std = fit_trend(window, checkpoint, target_x)
            differences = [abs(after[2] - before[2])
                           for before, after in zip(usable, usable[1:])]
            jump_std = middle(differences) / 0.6745 if differences else 0.0
            jump_variance = max(jump_std, 0.30) ** 2 * refreshes / 24.0
            spread = min(2.5, math.sqrt(rw_variance + fit_std ** 2
                                        + jump_variance + 0.15 ** 2))
        estimates.append((last_y, move, spread, bool(window)))
        tier_moves.setdefault(trophy["tier"], []).append(move)
    tier_centers = {tier: middle(moves) for tier, moves in tier_moves.items()}
    result = []
    for trophy, (last_y, move, spread, has_data) in zip(case["trophies"], estimates):
        # No observations in the window keeps the explicit missing-data prior.
        if has_data:
            move = 0.75 * move + 0.25 * tier_centers[trophy["tier"]]
        median_y = last_y + move
        quantiles = []
        previous = 0.01
        for score in NORMAL_SCORES:
            value = min(99.99, max(0.01, percent(median_y + score * spread)))
            previous = max(previous, value)
            quantiles.append(rounded_rate(previous))
        result.append({"id": trophy["id"], "q": quantiles})
    return {"trophies": result}


def main():
    source = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    destination = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    destination.mkdir(parents=True, exist_ok=True)
    for case_path in sorted(source.glob("*.in")):
        case = json.loads(case_path.read_text(encoding="utf-8"))
        encoded = json.dumps(forecast(case), allow_nan=False, separators=(",", ":"))
        output_path = destination / (str(case["id"]) + ".out")
        output_path.write_text(encoded + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
