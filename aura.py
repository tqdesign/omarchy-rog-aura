#!/usr/bin/env python3
"""ROG Aura control for the Omarchy under-glow plugin.

Reads asusd over D-Bus (`busctl --json=short`) and writes with `asusctl`.
No extra Python D-Bus packages are required.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

BUS = "xyz.ljones.Asusd"
AURA_IFACE = "xyz.ljones.Aura"
PROPS_IFACE = "org.freedesktop.DBus.Properties"

MODE_BY_ID = {
    0: "static",
    1: "breathe",
    2: "rainbow-cycle",
    3: "rainbow-wave",
    4: "stars",
    5: "rain",
    6: "highlight",
    7: "laser",
    8: "ripple",
    10: "pulse",
    11: "comet",
    12: "flash",
}
ID_BY_MODE = {name: mode_id for mode_id, name in MODE_BY_ID.items()}

ZONE_BY_ID = {
    0: "logo",
    1: "keyboard",
    2: "lightbar",
    3: "lid",
    4: "rear-glow",
    5: "keyboard-and-lightbar",
    6: "ally",
}
ID_BY_ZONE = {name: zone_id for zone_id, name in ZONE_BY_ID.items()}

ZONE_LABEL = {
    "logo": "Logo",
    "keyboard": "Keyboard",
    "lightbar": "Under glow",
    "lid": "Lid",
    "rear-glow": "Rear glow",
    "keyboard-and-lightbar": "Keyboard + bar",
    "ally": "Ally",
}

BRIGHTNESS_BY_ID = {0: "off", 1: "low", 2: "med", 3: "high"}
ID_BY_BRIGHTNESS = {name: bright_id for bright_id, name in BRIGHTNESS_BY_ID.items()}

EFFECT_ARGS = {
    "static": ("colour",),
    "breathe": ("colour", "colour2", "speed"),
    "rainbow-cycle": ("speed",),
    "rainbow-wave": ("speed", "direction"),
    "stars": ("colour", "colour2", "speed"),
    "rain": ("speed",),
    "highlight": ("colour", "speed"),
    "laser": ("colour", "speed"),
    "ripple": ("colour", "speed"),
    "pulse": ("colour",),
    "comet": ("colour",),
    "flash": ("colour",),
}

POWER_FLAGS = ("boot", "awake", "sleep", "shutdown")
AURA_PATH_RE = re.compile(r"/xyz/ljones/aura/[A-Za-z0-9_]+")
LID_POLL_SECONDS = 0.25


def state_path() -> Path:
    override = os.environ.get("OMARCHY_ROG_AURA_STATE")
    if override:
        return Path(override)
    return Path.home() / ".local/state/omarchy/rog-aura-lid.json"


def lid_state_paths() -> list[str]:
    override = os.environ.get("OMARCHY_ROG_AURA_LID")
    if override:
        return [override]
    return glob.glob("/proc/acpi/button/lid/*/state")


def lid_closed() -> bool:
    for path in lid_state_paths():
        try:
            if "closed" in Path(path).read_text():
                return True
        except OSError:
            continue
    return False


class AuraError(Exception):
    def __init__(self, message: str, available: bool = False) -> None:
        super().__init__(message)
        self.available = available


def emit(result: dict[str, Any], code: int | None = None) -> int:
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    if code is not None:
        return code
    return 0 if result.get("ok") else 1


def unwrap(node: Any) -> Any:
    """Flatten systemd `busctl --json=short` `{type, data}` wrappers."""
    if isinstance(node, dict):
        keys = set(node.keys())
        if "type" in node and "data" in node and keys <= {"type", "data"}:
            return unwrap(node["data"])
        return {key: unwrap(value) for key, value in node.items()}
    if isinstance(node, list):
        return [unwrap(item) for item in node]
    return node


def hex_colour(rgb: Any) -> str:
    if not isinstance(rgb, (list, tuple)) or len(rgb) < 3:
        return "000000"
    parts = []
    for value in rgb[:3]:
        try:
            parts.append(max(0, min(255, int(value))))
        except (TypeError, ValueError):
            parts.append(0)
    return f"{parts[0]:02x}{parts[1]:02x}{parts[2]:02x}"


def parse_hex(value: Any) -> str:
    raw = str(value or "").strip().lower().lstrip("#")
    if len(raw) == 3 and all(ch in "0123456789abcdef" for ch in raw):
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) >= 6 and all(ch in "0123456789abcdef" for ch in raw[:6]):
        return raw[:6]
    return "000000"


def rgb_from_hex(value: Any) -> tuple[int, int, int]:
    hex_colour = parse_hex(value)
    return int(hex_colour[0:2], 16), int(hex_colour[2:4], 16), int(hex_colour[4:6], 16)


def lower_token(value: Any, fallback: str) -> str:
    token = str(value or "").strip().lower()
    return token if token else fallback


def run_command(argv: list[str], timeout: float = 8.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def busctl_json(argv: list[str], runner: Callable[..., subprocess.CompletedProcess[str]] = run_command) -> Any:
    proc = runner(["busctl", "--json=short", *argv])
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "busctl failed").strip()
        raise AuraError(err or "busctl failed")
    try:
        return unwrap(json.loads(proc.stdout or "{}"))
    except json.JSONDecodeError as exc:
        raise AuraError(f"busctl JSON was not valid: {exc}") from exc


def find_aura_path(runner: Callable[..., subprocess.CompletedProcess[str]] = run_command) -> str:
    proc = runner(["busctl", "tree", "--system", BUS])
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        if "not provided" in err.lower() or "unknown name" in err.lower() or "not activatable" in err.lower():
            raise AuraError("asusd is not running")
        raise AuraError(err or "could not list asusd objects")
    matches = AURA_PATH_RE.findall(proc.stdout or "")
    if not matches:
        raise AuraError("no Aura device on this machine")
    return matches[0]


def props_from_getall(payload: Any) -> dict[str, Any]:
    data = payload
    if isinstance(data, list):
        merged: dict[str, Any] = {}
        for item in data:
            if isinstance(item, dict):
                merged.update(item)
        return merged
    if isinstance(data, dict):
        return data
    return {}


def parse_power_states(raw: Any, supported_ids: list[int]) -> list[dict[str, Any]]:
    rows = raw
    # `(a(ubbbb))` unwraps as [array_of_structs].
    if isinstance(rows, list) and rows and isinstance(rows[0], list) and (
        not rows[0] or isinstance(rows[0][0], list)
    ):
        rows = rows[0]
    by_id: dict[int, dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) < 5:
                continue
            try:
                zone_id = int(row[0])
            except (TypeError, ValueError):
                continue
            by_id[zone_id] = {
                "id": zone_id,
                "name": ZONE_BY_ID.get(zone_id, f"zone-{zone_id}"),
                "label": ZONE_LABEL.get(ZONE_BY_ID.get(zone_id, ""), f"Zone {zone_id}"),
                "boot": bool(row[1]),
                "awake": bool(row[2]),
                "sleep": bool(row[3]),
                "shutdown": bool(row[4]),
            }
    zones = []
    for zone_id in supported_ids:
        if zone_id in by_id:
            zones.append(by_id[zone_id])
        else:
            name = ZONE_BY_ID.get(zone_id, f"zone-{zone_id}")
            zones.append(
                {
                    "id": zone_id,
                    "name": name,
                    "label": ZONE_LABEL.get(name, f"Zone {zone_id}"),
                    "boot": False,
                    "awake": False,
                    "sleep": False,
                    "shutdown": False,
                }
            )
    return zones


def parse_status(props: dict[str, Any], path: str) -> dict[str, Any]:
    mode_data = props.get("LedModeData") or []
    if not isinstance(mode_data, list):
        mode_data = []
    mode_id = int(props.get("LedMode") or (mode_data[0] if mode_data else 0) or 0)
    colour = hex_colour(mode_data[2] if len(mode_data) > 2 else None)
    colour2 = hex_colour(mode_data[3] if len(mode_data) > 3 else None)
    speed = lower_token(mode_data[4] if len(mode_data) > 4 else "med", "med")
    direction = lower_token(mode_data[5] if len(mode_data) > 5 else "right", "right")
    brightness_id = int(props.get("Brightness") or 0)
    supported_modes = [
        MODE_BY_ID[int(item)]
        for item in (props.get("SupportedBasicModes") or [])
        if int(item) in MODE_BY_ID
    ]
    supported_brightness = [
        BRIGHTNESS_BY_ID[int(item)]
        for item in (props.get("SupportedBrightness") or [])
        if int(item) in BRIGHTNESS_BY_ID
    ]
    supported_power = [int(item) for item in (props.get("SupportedPowerZones") or [])]
    zones = parse_power_states(props.get("LedPower"), supported_power)
    mode = MODE_BY_ID.get(mode_id, "static")
    return {
        "ok": True,
        "available": True,
        "path": path,
        "mode": mode,
        "modeId": mode_id,
        "supportedModes": supported_modes or list(MODE_BY_ID.values()),
        "colour": colour,
        "colour2": colour2,
        "speed": speed if speed in ("low", "med", "high") else "med",
        "direction": direction if direction in ("left", "right", "up", "down") else "right",
        "brightness": BRIGHTNESS_BY_ID.get(brightness_id, "med"),
        "brightnessId": brightness_id,
        "supportedBrightness": supported_brightness or list(BRIGHTNESS_BY_ID.values()),
        "zones": zones,
        "lidClosed": lid_closed(),
        "error": None,
    }


def unavailable(message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "available": False,
        "path": "",
        "mode": "static",
        "modeId": 0,
        "supportedModes": list(MODE_BY_ID.values()),
        "colour": "000000",
        "colour2": "000000",
        "speed": "med",
        "direction": "right",
        "brightness": "off",
        "brightnessId": 0,
        "supportedBrightness": list(BRIGHTNESS_BY_ID.values()),
        "zones": [],
        "lidClosed": False,
        "error": message,
    }


def read_status(runner: Callable[..., subprocess.CompletedProcess[str]] = run_command) -> dict[str, Any]:
    path = find_aura_path(runner)
    payload = busctl_json(
        ["call", "--system", BUS, path, PROPS_IFACE, "GetAll", "s", AURA_IFACE],
        runner,
    )
    return parse_status(props_from_getall(payload), path)


def which_or_raise(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise AuraError(f"{name} is not installed")
    return path


def run_asusctl(args: list[str], runner: Callable[..., subprocess.CompletedProcess[str]] = run_command) -> None:
    binary = which_or_raise("asusctl")
    proc = runner([binary, *args])
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "asusctl failed").strip()
        raise AuraError(err or "asusctl failed", available=True)


def effect_fields(payload: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    mode = str(payload.get("mode") or current.get("mode") or "static")
    if mode not in EFFECT_ARGS:
        raise AuraError(f"unknown effect '{mode}'", available=True)
    speed = lower_token(payload.get("speed") or current.get("speed"), "med")
    if speed not in ("low", "med", "high"):
        speed = "med"
    direction = lower_token(payload.get("direction") or current.get("direction"), "right")
    if direction not in ("left", "right", "up", "down"):
        direction = "right"
    return {
        "mode": mode,
        "modeId": ID_BY_MODE[mode],
        "colour": parse_hex(payload.get("colour") or current.get("colour")),
        "colour2": parse_hex(payload.get("colour2") or current.get("colour2")),
        "speed": speed,
        "direction": direction,
    }


def apply_effect(payload: dict[str, Any], current: dict[str, Any], runner: Callable[..., subprocess.CompletedProcess[str]]) -> None:
    fields = effect_fields(payload, current)
    path = str(payload.get("path") or current.get("path") or "")
    if not path:
        path = find_aura_path(runner)
    colour = rgb_from_hex(fields["colour"])
    colour2 = rgb_from_hex(fields["colour2"])
    argv = [
        "busctl",
        "set-property",
        "--system",
        BUS,
        path,
        AURA_IFACE,
        "LedModeData",
        "(uu(yyy)(yyy)ss)",
        str(fields["modeId"]),
        "0",
        str(colour[0]),
        str(colour[1]),
        str(colour[2]),
        str(colour2[0]),
        str(colour2[1]),
        str(colour2[2]),
        fields["speed"].capitalize(),
        fields["direction"].capitalize(),
    ]
    proc = runner(argv)
    if proc.returncode == 0:
        return
    args = ["aura", "effect", fields["mode"]]
    needed = EFFECT_ARGS[fields["mode"]]
    if "colour" in needed:
        if fields["mode"] in ("static", "highlight", "laser", "ripple", "pulse", "comet", "flash"):
            args.extend(["-c", fields["colour"]])
        else:
            args.extend(["--colour", fields["colour"]])
    if "colour2" in needed:
        args.extend(["--colour2", fields["colour2"]])
    if "speed" in needed:
        args.extend(["--speed", fields["speed"]])
    if "direction" in needed:
        args.extend(["--direction", fields["direction"]])
    run_asusctl(args, runner)


def apply_power(payload: dict[str, Any], runner: Callable[..., subprocess.CompletedProcess[str]]) -> None:
    zone = str(payload.get("zone") or "")
    if zone not in ID_BY_ZONE:
        raise AuraError(f"unknown zone '{zone}'", available=True)
    args = ["aura", "power", zone]
    for flag in POWER_FLAGS:
        if bool(payload.get(flag)):
            args.append(f"--{flag}")
    run_asusctl(args, runner)


def apply_brightness(payload: dict[str, Any], runner: Callable[..., subprocess.CompletedProcess[str]]) -> None:
    value = lower_token(payload.get("value") or payload.get("brightness"), "med")
    if value not in ID_BY_BRIGHTNESS:
        raise AuraError(f"unknown brightness '{value}'", available=True)
    run_asusctl(["leds", "set", value], runner)


def load_lid_snapshot() -> dict[str, Any] | None:
    path = state_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def save_lid_snapshot(zones: list[Any]) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"zones": zones}), encoding="utf-8")


def clear_lid_snapshot() -> None:
    try:
        state_path().unlink()
    except FileNotFoundError:
        pass


def apply_lid(closed: bool, runner: Callable[..., subprocess.CompletedProcess[str]] = run_command) -> dict[str, Any]:
    current = read_status(runner)
    zones = current.get("zones") if isinstance(current.get("zones"), list) else []
    if closed:
        if load_lid_snapshot() is None:
            save_lid_snapshot(zones)
        for zone in zones:
            name = str(zone.get("name") or "")
            if name:
                apply_power({"zone": name}, runner)
    else:
        saved = load_lid_snapshot()
        saved_zones = saved.get("zones") if saved and isinstance(saved.get("zones"), list) else []
        for zone in saved_zones:
            if not isinstance(zone, dict):
                continue
            name = str(zone.get("name") or "")
            if not name:
                continue
            apply_power(
                {
                    "zone": name,
                    "boot": zone.get("boot"),
                    "awake": zone.get("awake"),
                    "sleep": zone.get("sleep"),
                    "shutdown": zone.get("shutdown"),
                },
                runner,
            )
        clear_lid_snapshot()
    result = read_status(runner)
    result["lidClosed"] = closed
    return result


def watch_lid(apply: bool = False, runner: Callable[..., subprocess.CompletedProcess[str]] = run_command) -> int:
    last: bool | None = None
    while True:
        closed = lid_closed()
        if closed != last:
            last = closed
            if apply:
                result = apply_lid(closed, runner)
            else:
                result = {"ok": True, "closed": closed}
            result["closed"] = closed
            emit(result)
        time.sleep(LID_POLL_SECONDS)


def apply_payload(payload: dict[str, Any], runner: Callable[..., subprocess.CompletedProcess[str]] = run_command) -> dict[str, Any]:
    live = payload.get("live") is True
    current = payload if payload.get("path") else read_status(runner)
    action = str(payload.get("action") or "effect")
    if action == "lid":
        return apply_lid(payload.get("closed") is True, runner)
    if action == "effect":
        apply_effect(payload, current, runner)
        if live:
            fields = effect_fields(payload, current)
            result = dict(current)
            result.update(fields)
            result["ok"] = True
            result["available"] = True
            result["lidClosed"] = lid_closed()
            result["error"] = None
            if result["lidClosed"]:
                return apply_lid(True, runner)
            return result
    elif action == "power":
        apply_power(payload, runner)
    elif action == "brightness":
        apply_brightness(payload, runner)
    else:
        raise AuraError(f"unknown action '{action}'", available=True)
    if lid_closed():
        return apply_lid(True, runner)
    return read_status(runner)


def load_payload(raw: str | None, path: str | None) -> dict[str, Any]:
    text = raw or ""
    if path:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    text = text.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AuraError(f"apply JSON was not valid: {exc}") from exc
    if not isinstance(parsed, dict):
        raise AuraError("apply JSON must be an object")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ROG Aura helper for the Omarchy plugin")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="print current Aura state as JSON")
    sub.add_parser("lid", help="print whether the laptop lid is closed")
    watch_cmd = sub.add_parser("watch-lid", help="emit JSON whenever the lid opens or closes")
    watch_cmd.add_argument("--apply", action="store_true", help="turn Aura off while the lid is closed")
    apply_cmd = sub.add_parser("apply", help="apply an effect, power, or brightness change")
    apply_cmd.add_argument("payload", nargs="?", help="JSON object")
    apply_cmd.add_argument("--file", dest="payload_file", help="read JSON from a file")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            return emit(read_status())
        if args.command == "lid":
            closed = lid_closed()
            return emit({"ok": True, "closed": closed, "lidClosed": closed})
        if args.command == "watch-lid":
            return watch_lid(apply=args.apply)
        payload = load_payload(args.payload, args.payload_file)
        return emit(apply_payload(payload))
    except AuraError as exc:
        if exc.available:
            try:
                result = read_status()
                result["ok"] = False
                result["error"] = str(exc)
                return emit(result, 1)
            except Exception:
                pass
        return emit(unavailable(str(exc)), 1)
    except subprocess.TimeoutExpired:
        return emit(unavailable("timed out talking to asusd"), 1)
    except FileNotFoundError as exc:
        return emit(unavailable(f"missing command: {exc.filename or exc}"), 1)
    except OSError as exc:
        return emit(unavailable(str(exc)), 1)


if __name__ == "__main__":
    raise SystemExit(main())
