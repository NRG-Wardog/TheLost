import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest import mock

import talkWithMicro as bridge


class FirebaseConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = {
            key: os.environ.get(key)
            for key in (
                "THELOST_FIREBASE_API_KEY",
                "THELOST_FIREBASE_AUTH_DOMAIN",
                "THELOST_FIREBASE_DATABASE_URL",
                "THELOST_FIREBASE_PROJECT_ID",
                "THELOST_FIREBASE_STORAGE_BUCKET",
                "THELOST_FIREBASE_MESSAGING_SENDER_ID",
                "THELOST_FIREBASE_APP_ID",
            )
        }
        for key in self.environment:
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        for key, value in self.environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_empty_environment_keeps_bridge_local_only(self) -> None:
        self.assertIsNone(bridge._firebase_config_from_env())

    def test_partial_environment_is_rejected(self) -> None:
        os.environ["THELOST_FIREBASE_API_KEY"] = "public-api-key"
        with self.assertRaisesRegex(ValueError, "databaseURL.*projectId"):
            bridge._firebase_config_from_env()

    def test_required_environment_builds_configuration(self) -> None:
        os.environ.update(
            {
                "THELOST_FIREBASE_API_KEY": "public-api-key",
                "THELOST_FIREBASE_DATABASE_URL": "https://example.invalid",
                "THELOST_FIREBASE_PROJECT_ID": "thelost-test",
            }
        )
        config = bridge._firebase_config_from_env()
        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(config["apiKey"], "public-api-key")
        self.assertEqual(config["databaseURL"], "https://example.invalid")
        self.assertEqual(config["projectId"], "thelost-test")


class RssiExtractionTests(unittest.TestCase):
    def test_advertisement_rssi_takes_precedence(self) -> None:
        device = SimpleNamespace(rssi=-80)
        advertisement = SimpleNamespace(rssi=-61)
        self.assertEqual(bridge._extract_rssi(device, advertisement), -61)

    def test_device_rssi_is_legacy_fallback(self) -> None:
        device = SimpleNamespace(rssi=-72)
        self.assertEqual(bridge._extract_rssi(device), -72)

    def test_missing_rssi_returns_none(self) -> None:
        self.assertIsNone(bridge._extract_rssi(SimpleNamespace()))


class MonitorBridgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_matching_device_publishes_normalized_sample(self) -> None:
        device = SimpleNamespace(address="AA:BB:CC:DD:EE:FF", rssi=-59)
        database = mock.MagicMock()
        child = database.child.return_value

        with (
            mock.patch.object(
                bridge,
                "_discover_devices",
                new=mock.AsyncMock(return_value=[(device, None)]),
            ),
            mock.patch.object(
                bridge.asyncio,
                "sleep",
                new=mock.AsyncMock(side_effect=asyncio.CancelledError),
            ),
        ):
            with self.assertRaises(asyncio.CancelledError):
                await bridge.monitor_device(
                    "aa:bb:cc:dd:ee:ff",
                    threshold_meters=5.0,
                    scan_interval_seconds=0.1,
                    measured_power=-59.0,
                    path_loss_exponent=2.0,
                    database=database,
                    firebase_path="alerts",
                )

        database.child.assert_called_once_with("alerts")
        child.push.assert_called_once_with(
            {"status": "close", "rssi": -59, "distance_meters": 1.0}
        )

    async def test_unmatched_device_does_not_publish(self) -> None:
        device = SimpleNamespace(address="11:22:33:44:55:66", rssi=-59)
        database = mock.MagicMock()

        with (
            mock.patch.object(
                bridge,
                "_discover_devices",
                new=mock.AsyncMock(return_value=[(device, None)]),
            ),
            mock.patch.object(
                bridge.asyncio,
                "sleep",
                new=mock.AsyncMock(side_effect=asyncio.CancelledError),
            ),
        ):
            with self.assertRaises(asyncio.CancelledError):
                await bridge.monitor_device(
                    "aa:bb:cc:dd:ee:ff",
                    threshold_meters=5.0,
                    scan_interval_seconds=0.1,
                    measured_power=-59.0,
                    path_loss_exponent=2.0,
                    database=database,
                    firebase_path="alerts",
                )

        database.child.assert_not_called()


if __name__ == "__main__":
    unittest.main()
