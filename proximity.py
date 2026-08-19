"""Pure proximity helpers for TheLost.

This module intentionally has no Bluetooth or Firebase dependencies so the
RSSI-to-distance behavior can be tested deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ProximitySample:
    """A normalized proximity observation."""

    rssi: int
    distance_meters: float
    status: str


def estimate_distance(
    rssi: int | float | None,
    *,
    measured_power: float = -59.0,
    path_loss_exponent: float = 2.0,
) -> float | None:
    """Estimate distance in meters from RSSI using a log-distance model.

    ``measured_power`` is the calibrated RSSI at 1 meter. The default value of
    -59 dBm is a common BLE starting point, but real deployments should
    calibrate it for their device and environment.
    """

    if rssi is None:
        return None
    if not isinstance(rssi, (int, float)) or isinstance(rssi, bool):
        raise TypeError("rssi must be a numeric value or None")
    if not math.isfinite(float(rssi)):
        raise ValueError("rssi must be finite")
    if path_loss_exponent <= 0:
        raise ValueError("path_loss_exponent must be greater than zero")

    return 10 ** ((measured_power - float(rssi)) / (10 * path_loss_exponent))


def classify_distance(distance_meters: float, *, threshold_meters: float = 5.0) -> str:
    """Classify a distance as ``close`` or ``far``."""

    if threshold_meters <= 0:
        raise ValueError("threshold_meters must be greater than zero")
    if distance_meters < 0 or not math.isfinite(distance_meters):
        raise ValueError("distance_meters must be a finite non-negative value")

    return "close" if distance_meters < threshold_meters else "far"


def build_sample(
    rssi: int,
    *,
    threshold_meters: float = 5.0,
    measured_power: float = -59.0,
    path_loss_exponent: float = 2.0,
) -> ProximitySample:
    """Convert one RSSI reading into a normalized proximity sample."""

    distance = estimate_distance(
        rssi,
        measured_power=measured_power,
        path_loss_exponent=path_loss_exponent,
    )
    assert distance is not None

    return ProximitySample(
        rssi=rssi,
        distance_meters=distance,
        status=classify_distance(distance, threshold_meters=threshold_meters),
    )
