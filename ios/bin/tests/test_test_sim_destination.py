import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_sim_destination import DestinationNotFoundError, select_destination


def runtime(identifier: str, version: str) -> dict[str, object]:
    return {"identifier": identifier, "version": version, "isAvailable": True}


def device(name: str, udid: str) -> dict[str, object]:
    return {"name": name, "udid": udid, "isAvailable": True}


class SelectDestinationTests(unittest.TestCase):
    def test_selects_requested_older_model_instead_of_latest_os_model(self) -> None:
        ios_18 = "com.apple.CoreSimulator.SimRuntime.iOS-18-6"
        ios_26 = "com.apple.CoreSimulator.SimRuntime.iOS-26-1"
        selected = select_destination(
            {
                "devices": {
                    ios_26: [device("iPhone 17 Pro", "NEWEST-OS")],
                    ios_18: [device("iPhone 16 Pro", "REQUESTED")],
                }
            },
            {"runtimes": [runtime(ios_26, "26.1"), runtime(ios_18, "18.6")]},
            model="iPhone 16 Pro",
            ios_major=18,
        )

        self.assertEqual(selected.udid, "REQUESTED")
        self.assertEqual(selected.version, "18.6")

    def test_selects_highest_same_major_independent_of_json_order(self) -> None:
        ios_18_5 = "com.apple.CoreSimulator.SimRuntime.iOS-18-5"
        ios_18_6 = "com.apple.CoreSimulator.SimRuntime.iOS-18-6"
        payloads = [
            (
                {ios_18_5: [device("iPhone 16 Pro", "OLD")], ios_18_6: [device("iPhone 16 Pro", "B")]},
                [runtime(ios_18_5, "18.5"), runtime(ios_18_6, "18.6")],
            ),
            (
                {ios_18_6: [device("iPhone 16 Pro", "B")], ios_18_5: [device("iPhone 16 Pro", "OLD")]},
                [runtime(ios_18_6, "18.6"), runtime(ios_18_5, "18.5")],
            ),
        ]

        for devices, runtimes in payloads:
            with self.subTest(order=list(devices)):
                selected = select_destination(
                    {"devices": devices},
                    {"runtimes": runtimes},
                    model="iPhone 16 Pro",
                    ios_major=18,
                )
                self.assertEqual((selected.version, selected.udid), ("18.6", "B"))

    def test_same_version_uses_lexicographically_stable_udid(self) -> None:
        ios_18 = "com.apple.CoreSimulator.SimRuntime.iOS-18-6"
        selected = select_destination(
            {"devices": {ios_18: [device("iPhone 16 Pro", "B"), device("iPhone 16 Pro", "A")]}},
            {"runtimes": [runtime(ios_18, "18.6")]},
            model="iPhone 16 Pro",
            ios_major=18,
        )

        self.assertEqual(selected.udid, "A")

    def test_missing_request_diagnostic_lists_request_candidates_and_guidance(self) -> None:
        ios_26 = "com.apple.CoreSimulator.SimRuntime.iOS-26-1"
        with self.assertRaises(DestinationNotFoundError) as raised:
            select_destination(
                {"devices": {ios_26: [device("iPhone 17 Pro", "ONLY-DEVICE")]}},
                {"runtimes": [runtime(ios_26, "26.1")]},
                model="iPhone 16 Pro",
                ios_major=18,
            )

        message = str(raised.exception)
        self.assertIn("iPhone 16 Pro", message)
        self.assertIn("iOS major 18", message)
        self.assertIn("iPhone 17 Pro, iOS 26.1, UDID ONLY-DEVICE", message)
        self.assertIn("Install", message)
        self.assertIn("--model/--ios-major", message)

    def test_explicit_udid_override_selects_that_available_device(self) -> None:
        ios_26 = "com.apple.CoreSimulator.SimRuntime.iOS-26-1"
        selected = select_destination(
            {"devices": {ios_26: [device("iPhone 17 Pro", "OVERRIDE")]}},
            {"runtimes": [runtime(ios_26, "26.1")]},
            model="iPhone 16 Pro",
            ios_major=18,
            udid="OVERRIDE",
        )

        self.assertEqual((selected.name, selected.version), ("iPhone 17 Pro", "26.1"))


if __name__ == "__main__":
    unittest.main()
