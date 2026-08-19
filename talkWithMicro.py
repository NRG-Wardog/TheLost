"""BLE proximity bridge for TheLost.

The script scans for one BLE device, converts RSSI readings into coarse
proximity estimates, and optionally publishes samples to Firebase Realtime
Database. All deployment-specific configuration is supplied through CLI flags
or environment variables rather than being embedded in source code.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from typing import Any

from bleak import BleakScanner
import pyrebase

from proximity import build_sample


LOGGER = logging.getLogger("thelost")


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return default if raw in (None, "") else float(raw)


def _firebase_config_from_env() -> dict[str, str] | None:
    """Return a Pyrebase configuration when the required values are present.

    Firebase publishing is optional. A missing configuration keeps the bridge
    useful as a local BLE proximity monitor.
    """

    mapping = {
        "apiKey": "THELOST_FIREBASE_API_KEY",
        "authDomain": "THELOST_FIREBASE_AUTH_DOMAIN",
        "databaseURL": "THELOST_FIREBASE_DATABASE_URL",
        "projectId": "THELOST_FIREBASE_PROJECT_ID",
        "storageBucket": "THELOST_FIREBASE_STORAGE_BUCKET",
        "messagingSenderId": "THELOST_FIREBASE_MESSAGING_SENDER_ID",
        "appId": "THELOST_FIREBASE_APP_ID",
    }

    config = {key: os.getenv(env_name, "").strip() for key, env_name in mapping.items()}
    required = ("apiKey", "databaseURL", "projectId")

    if not any(config.values()):
        return None
    if not all(config[key] for key in required):
        missing = [key for key in required if not config[key]]
        raise ValueError(
            "Incomplete Firebase configuration; missing required values: "
            + ", ".join(missing)
        )

    return config


def _create_database() -> Any | None:
    config = _firebase_config_from_env()
    if config is None:
        LOGGER.info("Firebase is not configured; running in local-only mode")
        return None

    firebase = pyrebase.initialize_app(config)
    LOGGER.info("Firebase publishing enabled")
    return firebase.database()


def _extract_rssi(device: Any, advertisement: Any | None = None) -> int | None:
    """Read RSSI across Bleak versions without coupling the rest of the code."""

    if advertisement is not None:
        value = getattr(advertisement, "rssi", None)
        if value is not None:
            return int(value)

    value = getattr(device, "rssi", None)
    return None if value is None else int(value)


async def _discover_devices() -> list[tuple[Any, Any | None]]:
    """Discover BLE devices while supporting old and new Bleak result shapes."""

    try:
        discovered = await BleakScanner.discover(return_adv=True)
    except TypeError:
        # Compatibility path for older Bleak versions.
        devices = await BleakScanner.discover()
        return [(device, None) for device in devices]

    return list(discovered.values())


async def monitor_device(
    target_address: str,
    *,
    threshold_meters: float,
    scan_interval_seconds: float,
    measured_power: float,
    path_loss_exponent: float,
    database: Any | None,
    firebase_path: str,
) -> None:
    """Continuously monitor one BLE address and publish normalized samples."""

    normalized_target = target_address.lower()
    LOGGER.info(
        "Monitoring %s with %.2fm threshold",
        target_address,
        threshold_meters,
    )

    while True:
        try:
            discovered = await _discover_devices()
            match = None

            for device, advertisement in discovered:
                address = getattr(device, "address", "")
                if address.lower() == normalized_target:
                    match = (device, advertisement)
                    break

            if match is None:
                LOGGER.debug("Target device not observed in this scan")
            else:
                device, advertisement = match
                rssi = _extract_rssi(device, advertisement)

                if rssi is None:
                    LOGGER.warning("Target device was observed without an RSSI value")
                else:
                    sample = build_sample(
                        rssi,
                        threshold_meters=threshold_meters,
                        measured_power=measured_power,
                        path_loss_exponent=path_loss_exponent,
                    )
                    payload = {
                        "status": sample.status,
                        "rssi": sample.rssi,
                        "distance_meters": round(sample.distance_meters, 2),
                    }

                    LOGGER.info(
                        "device=%s rssi=%sdBm distance=%.2fm status=%s",
                        target_address,
                        sample.rssi,
                        sample.distance_meters,
                        sample.status,
                    )

                    if database is not None:
                        database.child(firebase_path).push(payload)

        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("BLE scan cycle failed")

        await asyncio.sleep(scan_interval_seconds)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor BLE proximity for TheLost")
    parser.add_argument(
        "--target-address",
        default=os.getenv("THELOST_TARGET_ADDRESS"),
        help="BLE address to monitor (or set THELOST_TARGET_ADDRESS)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=_env_float("THELOST_DISTANCE_THRESHOLD_METERS", 5.0),
        help="close/far threshold in meters (default: 5)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=_env_float("THELOST_SCAN_INTERVAL_SECONDS", 2.0),
        help="seconds between scans (default: 2)",
    )
    parser.add_argument(
        "--measured-power",
        type=float,
        default=_env_float("THELOST_MEASURED_POWER_DBM", -59.0),
        help="calibrated RSSI at 1 meter (default: -59 dBm)",
    )
    parser.add_argument(
        "--path-loss-exponent",
        type=float,
        default=_env_float("THELOST_PATH_LOSS_EXPONENT", 2.0),
        help="environmental path-loss exponent (default: 2.0)",
    )
    parser.add_argument(
        "--firebase-path",
        default=os.getenv("THELOST_FIREBASE_ALERT_PATH", "alerts"),
        help="Realtime Database child path (default: alerts)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="enable debug logging",
    )
    args = parser.parse_args()

    if not args.target_address:
        parser.error("--target-address or THELOST_TARGET_ADDRESS is required")
    if args.threshold <= 0:
        parser.error("--threshold must be greater than zero")
    if args.interval <= 0:
        parser.error("--interval must be greater than zero")
    if args.path_loss_exponent <= 0:
        parser.error("--path-loss-exponent must be greater than zero")

    return args


def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    database = _create_database()

    try:
        asyncio.run(
            monitor_device(
                args.target_address,
                threshold_meters=args.threshold,
                scan_interval_seconds=args.interval,
                measured_power=args.measured_power,
                path_loss_exponent=args.path_loss_exponent,
                database=database,
                firebase_path=args.firebase_path,
            )
        )
    except KeyboardInterrupt:
        LOGGER.info("Stopped by user")


if __name__ == "__main__":
    main()
