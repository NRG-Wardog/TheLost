# TheLost

[![Python tests](https://github.com/NRG-Wardog/TheLost/actions/workflows/python-tests.yml/badge.svg)](https://github.com/NRG-Wardog/TheLost/actions/workflows/python-tests.yml)

**BLE Proximity Safety Prototype — Android, Python & Firebase**

TheLost is a hackathon prototype exploring a simple idea: detect when a tracked Bluetooth Low Energy (BLE) device moves beyond a configurable proximity threshold and surface that state to the user.

The repository contains two proof-of-concept paths built around the same proximity concept:

- **Android client** — scans for a named BLE / micro:bit device, estimates distance from RSSI, and raises a local notification when the device is too far away.
- **Python bridge** — scans for a specific BLE address, converts RSSI to an approximate distance, classifies the device as `close` / `far`, and can publish status samples to Firebase Realtime Database.

> **Project status:** Hackathon prototype. The core BLE discovery, RSSI-based proximity logic, Android alert flow, and Firebase publishing path were implemented. The event ended before the Android and cloud paths were unified into one production-ready application, so the repository is intentionally presented as a tested engineering prototype rather than a finished tracking product.

---

## Architecture

```text
                    ┌──────────────────────────┐
                    │ BLE device / micro:bit   │
                    └────────────┬─────────────┘
                                 │ BLE advertisements / RSSI
                    ┌────────────┴─────────────┐
                    │                          │
                    ▼                          ▼
        ┌─────────────────────┐    ┌────────────────────────┐
        │ Android application │    │ Python BLE bridge      │
        │ Java                │    │ Bleak                  │
        │                     │    │                        │
        │ Scan by device name │    │ Scan by BLE address    │
        │ Estimate proximity  │    │ Estimate proximity     │
        │ Local notification  │    │ Classify close / far   │
        └─────────────────────┘    └────────────┬───────────┘
                                               │
                                               ▼
                                  ┌────────────────────────┐
                                  │ Firebase Realtime DB   │
                                  │ proximity status data  │
                                  └────────────────────────┘
```

---

## Engineering Highlights

- BLE discovery from both **Android** and **Python**.
- RSSI-based distance approximation with configurable calibration parameters.
- Separation of proximity estimation from device/cloud integration so the core logic can be tested independently.
- Android notification flow for out-of-range events.
- Firebase Realtime Database integration for publishing proximity state.
- Environment-driven configuration for BLE target, Firebase settings, threshold, and scan interval.
- Deterministic unit tests for the pure proximity model.
- GitHub Actions compatibility checks across Python 3.10, 3.11, and 3.12.

---

## Repository Layout

```text
TheLost/
├── app/                      # Android application (Java / Gradle)
├── proximity.py              # Pure RSSI -> distance / status logic
├── talkWithMicro.py          # Python BLE + Firebase bridge
├── tests/                    # Unit tests for proximity logic
├── requirements.txt          # Python runtime dependencies
└── README.md
```

---

## Python BLE Bridge

### Requirements

- Python 3.10+
- Bluetooth adapter supported by [Bleak](https://github.com/hbldh/bleak)
- Firebase Realtime Database only if cloud publishing is enabled

Install dependencies:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Configure

Deployment-specific values are supplied through environment variables instead of being embedded in source code.

```text
THELOST_TARGET_ADDRESS=C4:A7:D8:EE:A2:39
THELOST_DISTANCE_THRESHOLD_METERS=5
THELOST_SCAN_INTERVAL_SECONDS=2

THELOST_FIREBASE_API_KEY=...
THELOST_FIREBASE_AUTH_DOMAIN=...
THELOST_FIREBASE_DATABASE_URL=https://<project>.firebaseio.com/
THELOST_FIREBASE_PROJECT_ID=...
THELOST_FIREBASE_STORAGE_BUCKET=...
THELOST_FIREBASE_MESSAGING_SENDER_ID=...
THELOST_FIREBASE_APP_ID=...
THELOST_FIREBASE_ALERT_PATH=alerts
```

Run:

```bash
python talkWithMicro.py
```

Common values can also be overridden from the CLI:

```bash
python talkWithMicro.py \
  --target-address C4:A7:D8:EE:A2:39 \
  --threshold 5 \
  --interval 2
```

If Firebase configuration is omitted, the bridge remains useful as a local BLE proximity monitor and does not attempt cloud writes.

---

## Android App

The Android prototype lives under `app/` and targets a BLE device named `The_Lost_Microbit`.

Implemented flow:

1. Scan for BLE advertisements.
2. Match the target micro:bit device name.
3. Read RSSI from the scan result.
4. Estimate proximity.
5. Raise a local notification when the configured threshold is crossed.

The Android path is a proof of concept rather than a hardened long-running background tracking service.

---

## Proximity Model

BLE RSSI is noisy and is affected by walls, device orientation, radio hardware, interference, and calibration.

The Python path uses the log-distance approximation:

```text
distance = 10 ^ ((measured_power - RSSI) / (10 * path_loss_exponent))
```

This is useful for **coarse proximity classification**, not precise physical ranging.

---

## Tests

```bash
python -m unittest discover -s tests -v
```

The tests cover:

- expected distance at the calibrated 1-meter RSSI value;
- monotonic distance behavior as RSSI weakens;
- invalid RSSI handling;
- `close` / `far` threshold classification.

CI also compiles the Python sources and runs the suite on Python 3.10, 3.11, and 3.12.

---

## Known Limitations

- RSSI-based distance is approximate, not centimeter-accurate ranging.
- The Android and Firebase paths are not currently connected into one end-to-end mobile/cloud workflow.
- The Android implementation does not provide hardened long-running background BLE monitoring.
- Device calibration is environment-specific.
- Firebase access rules and authentication must be configured appropriately for any real deployment.

---

## License

MIT — see [`LICENSE.md`](LICENSE.md).
