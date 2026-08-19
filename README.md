# TheLost

**BLE Proximity Safety Prototype — Android, Python & Firebase**

TheLost is a hackathon prototype exploring a simple idea: detect when a tracked Bluetooth Low Energy (BLE) device moves beyond a configurable proximity threshold and surface that state to the user.

The repository contains two proof-of-concept paths built around the same proximity concept:

- **Android client** — scans for a named BLE / micro:bit device, estimates distance from RSSI, and raises a local notification when the device is too far away.
- **Python bridge** — scans for a specific BLE address, converts RSSI to an approximate distance, classifies the device as `close` / `far`, and can publish status samples to Firebase Realtime Database.

> **Project status:** Hackathon prototype. The core BLE discovery, RSSI-based proximity logic, Android alert flow, and Firebase publishing path were implemented. The original event ended before the Android and cloud paths were unified into one production-ready application. The repository is preserved as an engineering prototype rather than presented as a finished tracking product.

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
- Separation of proximity estimation from device / cloud integration so the core logic can be tested independently.
- Android notification flow for out-of-range events.
- Firebase Realtime Database integration for publishing proximity state.
- Environment-driven configuration for BLE target, Firebase settings, threshold, and scan interval.
- Unit tests for the pure proximity model.
- Lightweight GitHub Actions validation for the proximity logic.

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

The script no longer depends on a hard-coded BLE address or Firebase project configuration.

Example environment variables:

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

You can also override common settings from the CLI:

```bash
python talkWithMicro.py \
  --target-address C4:A7:D8:EE:A2:39 \
  --threshold 5 \
  --interval 2
```

If Firebase configuration is omitted, the bridge still performs local BLE scanning and logs proximity results without attempting cloud writes.

---

## Android App

The Android prototype lives under `app/` and targets a BLE device named `The_Lost_Microbit`.

Implemented flow:

1. Start the application.
2. Scan for BLE advertisements.
3. Match the configured micro:bit device name.
4. Read RSSI from the scan result.
5. Estimate proximity.
6. Raise a notification when the distance crosses the configured threshold.

The app was built as part of the hackathon prototype and should be treated as a proof of concept rather than a production background-tracking implementation.

---

## Proximity Model

BLE RSSI is noisy and is affected by walls, device orientation, radio hardware, interference, and calibration.

The Python path uses the standard log-distance approximation:

```text
distance = 10 ^ ((measured_power - RSSI) / (10 * path_loss_exponent))
```

This is useful for **coarse proximity classification**, not precise physical ranging.

---

## Tests

Run the unit tests for the pure proximity model:

```bash
python -m unittest discover -s tests -v
```

The tests cover:

- expected distance at the calibrated 1-meter RSSI value
- monotonic distance behavior as RSSI weakens
- invalid RSSI handling
- `close` / `far` threshold classification

---

## Known Limitations

- RSSI-based distance is approximate, not centimeter-accurate ranging.
- The Android and Firebase paths are not currently connected into a single end-to-end mobile/cloud workflow.
- The Android implementation is a prototype and does not provide hardened long-running background BLE monitoring.
- Device calibration is environment-specific.
- Firebase access rules and authentication must be configured appropriately for any real deployment.

---

## Why Keep This Project Public?

TheLost is not presented as a finished product. It is kept as a record of an earlier engineering prototype covering **BLE, Android, asynchronous Python, cloud integration, and proximity modeling**.

It complements later projects by showing experimentation with hardware-adjacent software and cross-component system design under hackathon constraints.

---

## License

MIT — see [`LICENSE.md`](LICENSE.md).
