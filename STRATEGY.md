# Forecast strategy

This entry implements the specified model without tuning to practice answers. Exophase refreshes can enlarge the tracked player base faster than earned counts, diluting rates. Flat reads therefore support a persistent median but cannot justify an arbitrarily narrow interval.

- Fit each trophy in logit space against log elapsed time using a 48-hour window and exponential recency weights with a 24-hour decay.
- Require at least three distinct observation times; otherwise persist with a 0.6 fit uncertainty.
- Dampen the fitted move by `R / (R + H)` in log time, limiting unsupported long extrapolation, then shrink moves 25% toward their tier median.
- Use weighted population residual variance (`sum(w * residual²) / sum(w)`) and the specified target leverage. Window boundaries and weight ages are measured from the checkpoint; null rates are skipped per trophy.
- Estimate refresh jumps from the median absolute consecutive usable logit change across the supplied history, divided by 0.6745. Retain the 0.30 prior even for flat histories, scaling by the expected number of six-hour refreshes and dividing by the square root of 24.
- Combine jump, fit, `0.5 * sqrt(horizon_days)` random-walk, and 0.15 floor uncertainties in quadrature, capped at 2.5. A trophy with no usable window observations retains its last known rate (or 1%) and spread 2.0 without tier borrowing.
- Transform the five specified normal scores back to percentages, clamp to 0.01–99.99, enforce monotonicity, and round half up to four decimals.

The log-time transform preserves the slightly pre-midnight practice observation. For an observation at least one hour before the origin, where the mathematical transform is undefined, its argument is bounded above zero to keep the forecast finite. The model reads only supplied case data and has no external state.
