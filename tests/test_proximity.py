import math
import unittest

from proximity import build_sample, classify_distance, estimate_distance


class EstimateDistanceTests(unittest.TestCase):
    def test_calibrated_rssi_is_one_meter(self):
        self.assertAlmostEqual(estimate_distance(-59), 1.0, places=6)

    def test_weaker_signal_means_greater_distance(self):
        near = estimate_distance(-60)
        far = estimate_distance(-80)
        self.assertIsNotNone(near)
        self.assertIsNotNone(far)
        self.assertGreater(far, near)

    def test_none_rssi_returns_none(self):
        self.assertIsNone(estimate_distance(None))

    def test_invalid_path_loss_exponent_is_rejected(self):
        with self.assertRaises(ValueError):
            estimate_distance(-70, path_loss_exponent=0)

    def test_non_finite_rssi_is_rejected(self):
        with self.assertRaises(ValueError):
            estimate_distance(math.inf)


class ClassificationTests(unittest.TestCase):
    def test_close_below_threshold(self):
        self.assertEqual(classify_distance(4.99, threshold_meters=5.0), "close")

    def test_far_at_threshold(self):
        self.assertEqual(classify_distance(5.0, threshold_meters=5.0), "far")

    def test_build_sample_normalizes_observation(self):
        sample = build_sample(-59, threshold_meters=5.0)
        self.assertEqual(sample.rssi, -59)
        self.assertEqual(sample.status, "close")
        self.assertAlmostEqual(sample.distance_meters, 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
