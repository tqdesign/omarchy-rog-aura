#!/usr/bin/env python3
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import aura

GETALL = {
    "type": "a{sv}",
    "data": [
        {
            "SupportedBasicModes": {
                "type": "au",
                "data": [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12],
            },
            "LedModeData": {
                "type": "(uu(yyy)(yyy)ss)",
                "data": [0, 0, [38, 187, 217], [0, 0, 0], "Med", "Right"],
            },
            "Brightness": {"type": "u", "data": 2},
            "SupportedPowerZones": {"type": "au", "data": [1, 2]},
            "SupportedBrightness": {"type": "au", "data": [0, 1, 2, 3]},
            "SupportedBasicZones": {"type": "au", "data": []},
            "LedMode": {"type": "u", "data": 0},
            "LedPower": {
                "type": "(a(ubbbb))",
                "data": [[[1, True, True, True, True], [2, True, True, False, False]]],
            },
            "DeviceType": {"type": "u", "data": 0},
        }
    ],
}

TREE = """└─ /xyz
  └─ /xyz/ljones
    └─ /xyz/ljones/aura
      └─ /xyz/ljones/aura/19b6_2_4
"""


def completed(stdout="", stderr="", returncode=0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


class AuraTests(unittest.TestCase):
    def test_unwrap_getall(self):
        props = aura.props_from_getall(aura.unwrap(GETALL))
        self.assertEqual(props["LedMode"], 0)
        self.assertEqual(props["LedModeData"][2], [38, 187, 217])
        status = aura.parse_status(props, "/xyz/ljones/aura/19b6_2_4")
        self.assertTrue(status["ok"])
        self.assertEqual(status["mode"], "static")
        self.assertEqual(status["colour"], "26bbd9")
        self.assertEqual(status["speed"], "med")
        names = [z["name"] for z in status["zones"]]
        self.assertEqual(names, ["keyboard", "lightbar"])
        lightbar = status["zones"][1]
        self.assertTrue(lightbar["awake"])
        self.assertFalse(lightbar["sleep"])
        self.assertEqual(lightbar["label"], "Under glow")
        self.assertIn("pulse", status["supportedModes"])
        self.assertIn("flash", status["supportedModes"])

    def test_hex_and_payload_helpers(self):
        self.assertEqual(aura.parse_hex("#F0A"), "ff00aa")
        self.assertEqual(aura.hex_colour([38, 187, 217]), "26bbd9")

    def test_find_path(self):
        def runner(argv):
            self.assertEqual(argv[:3], ["busctl", "tree", "--system"])
            return completed(TREE)

        self.assertEqual(aura.find_aura_path(runner), "/xyz/ljones/aura/19b6_2_4")

    def test_apply_effect_command(self):
        calls = []

        def runner(argv):
            calls.append(argv)
            if argv[:2] == ["busctl", "tree"]:
                return completed(TREE)
            if argv[0] == "busctl" and "GetAll" in argv:
                return completed(json.dumps(GETALL))
            if argv[0] == "busctl" and "set-property" in argv:
                return completed()
            if argv[0].endswith("asusctl") or argv[0] == "asusctl":
                return completed()
            return completed(returncode=1, stderr="unexpected")

        status = aura.read_status(runner)
        self.assertEqual(status["colour"], "26bbd9")
        aura.apply_effect({"mode": "breathe", "colour": "ff0000"}, status, runner)
        setp = [c for c in calls if c and c[0] == "busctl" and "set-property" in c][-1]
        self.assertEqual(
            setp,
            [
                "busctl",
                "set-property",
                "--system",
                "xyz.ljones.Asusd",
                "/xyz/ljones/aura/19b6_2_4",
                "xyz.ljones.Aura",
                "LedModeData",
                "(uu(yyy)(yyy)ss)",
                "1",
                "0",
                "255",
                "0",
                "0",
                "0",
                "0",
                "0",
                "Med",
                "Right",
            ],
        )

    def test_unavailable(self):
        def runner(argv):
            return completed(returncode=1, stderr="The name xyz.ljones.Asusd was not provided")

        with self.assertRaises(aura.AuraError):
            aura.find_aura_path(runner)

    def test_lid_closed_and_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            lid = Path(tmp) / "lid"
            state = Path(tmp) / "snap.json"
            lid.write_text("state:      closed\n")
            os.environ["OMARCHY_ROG_AURA_LID"] = str(lid)
            os.environ["OMARCHY_ROG_AURA_STATE"] = str(state)
            self.addCleanup(lambda: os.environ.pop("OMARCHY_ROG_AURA_LID", None))
            self.addCleanup(lambda: os.environ.pop("OMARCHY_ROG_AURA_STATE", None))
            self.assertTrue(aura.lid_closed())
            lid.write_text("state:      open\n")
            self.assertFalse(aura.lid_closed())

            calls = []

            def runner(argv):
                calls.append(argv)
                if argv[:2] == ["busctl", "tree"]:
                    return completed(TREE)
                if argv[0] == "busctl" and "GetAll" in argv:
                    return completed(json.dumps(GETALL))
                if argv[0] == "busctl" and "set-property" in argv:
                    return completed()
                if argv[0].endswith("asusctl") or argv[0] == "asusctl":
                    return completed()
                return completed(returncode=1, stderr="unexpected")

            original_which = aura.which_or_raise
            aura.which_or_raise = lambda name: "/usr/bin/asusctl"
            try:
                closed = aura.apply_lid(True, runner)
                self.assertTrue(state.is_file())
                self.assertTrue(closed["lidClosed"])
                power = [c for c in calls if c[:3] == ["/usr/bin/asusctl", "aura", "power"]]
                self.assertEqual(power[0], ["/usr/bin/asusctl", "aura", "power", "keyboard"])
                self.assertEqual(power[1], ["/usr/bin/asusctl", "aura", "power", "lightbar"])
                calls.clear()
                opened = aura.apply_lid(False, runner)
                self.assertFalse(state.is_file())
                restored = [c for c in calls if c[:3] == ["/usr/bin/asusctl", "aura", "power"]]
                self.assertEqual(
                    restored[0],
                    ["/usr/bin/asusctl", "aura", "power", "keyboard", "--boot", "--awake", "--sleep", "--shutdown"],
                )
                self.assertEqual(
                    restored[1],
                    ["/usr/bin/asusctl", "aura", "power", "lightbar", "--boot", "--awake"],
                )
                self.assertFalse(opened["lidClosed"])
            finally:
                aura.which_or_raise = original_which


if __name__ == "__main__":
    unittest.main()
