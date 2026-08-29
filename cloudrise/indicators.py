from __future__ import annotations

import math
import statistics
from collections.abc import Sequence


def clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def ema(values: Sequence[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    output = [float(values[0])]
    for value in values[1:]:
        output.append(alpha * float(value) + (1.0 - alpha) * output[-1])
    return output


def rsi(values: Sequence[float], period: int = 14) -> float:
    if len(values) <= period:
        return 50.0
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(change, 0.0) for change in changes[-period:]]
    losses = [max(-change, 0.0) for change in changes[-period:]]
    average_gain = sum(gains) / period
    average_loss = sum(losses) / period
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def realized_volatility(values: Sequence[float], bars_per_year: int = 6552) -> float:
    if len(values) < 3:
        return 0.0
    returns = [math.log(values[i] / values[i - 1]) for i in range(1, len(values)) if values[i - 1] > 0]
    if len(returns) < 2:
        return 0.0
    return statistics.stdev(returns) * math.sqrt(bars_per_year)


def average_true_range(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> float:
    if len(closes) < 2:
        return 0.0
    true_ranges = []
    for index in range(1, len(closes)):
        true_ranges.append(
            max(
                highs[index] - lows[index],
                abs(highs[index] - closes[index - 1]),
                abs(lows[index] - closes[index - 1]),
            )
        )
    window = true_ranges[-period:]
    return sum(window) / max(len(window), 1)

