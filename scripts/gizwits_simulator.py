#!/usr/bin/env python3
"""Gizwits cloud API simulator for Aqua Medic devices.

Simulates the Gizwits REST API endpoints used by the ha-aquamedic-component
integration, allowing integration testing without real hardware or cloud access.

Endpoints simulated:
    POST /app/provision          → always succeeds
    POST /app/login              → validates username/password from config
    GET  /app/bindings           → returns configured virtual devices
    GET  /app/devdata/<did>/latest → returns live device attributes
    POST /app/control/<did>      → updates device attributes
    GET  /app/datapoint          → returns datapoint schema for a product_key

Usage:
    sudo python3 gizwits_simulator.py [-c config.json]

    sudo is required to bind a virtual IP on eth0.
    Default config file: gizwits_sim_config.json (same directory as script).

Config format (gizwits_sim_config.json):
    {
        "username": "test@example.com",
        "password": "secret",
        "virtual_ip": "192.168.100.10",
        "interface": "eth0",
        "port": 8080,
        "devices": [
            {"type": "smartdrift", "count": 2},
            {"type": "dc_runner",  "count": 1},
            {"type": "dc_skimmer", "count": 1}
        ]
    }

    "interface" is optional: if omitted, the default-route interface is
    auto-detected (falling back to eth0). It can also be overridden on the
    command line with -i/--interface.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from optparse import OptionParser
from typing import Any

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("gizwits-sim")

# ── Known product keys (must match const.py) ──────────────────────────────────

SMARTDRIFT_PRODUCT_KEY = "63632f4902094055ab3fd994c0d612fa"
# DC Runner series firmware — used by both return-pump and skimmer variants.
DC_RUNNER_SERIES_PRODUCT_KEY = "00276aa006684c05805c297f60058c3d"
# Speculative simpler variant (kept for backward-compat, never captured live).
DC_RUNNER_LEGACY_PRODUCT_KEY = "8879684725d14066922374e50889f893"

# Legacy names kept as aliases so old sim configs still work verbatim.
DC_RUNNER_PRODUCT_KEY = DC_RUNNER_LEGACY_PRODUCT_KEY
DC_SKIMMER_PRODUCT_KEY = DC_RUNNER_SERIES_PRODUCT_KEY

PRODUCT_KEYS: dict[str, str] = {
    "smartdrift": SMARTDRIFT_PRODUCT_KEY,
    # dc_runner keeps its speculative legacy key so old configs behave as before.
    "dc_runner": DC_RUNNER_LEGACY_PRODUCT_KEY,
    # dc_runner_return is the modern return-pump variant that shares the DC Runner
    # series firmware with the skimmer — same product_key, same datapoint schema.
    "dc_runner_return": DC_RUNNER_SERIES_PRODUCT_KEY,
    "dc_skimmer": DC_RUNNER_SERIES_PRODUCT_KEY,
}

PRODUCT_NAMES: dict[str, str] = {
    "smartdrift": "Current_Pump",
    "dc_runner": "DC_Runner",
    "dc_runner_return": "DC_Runner",
    "dc_skimmer": "DC_Runner",
}

# ── Default attribute state per device type ───────────────────────────────────


def _default_attrs_smartdrift() -> dict[str, Any]:
    """Initial attribute state for a SmartDrift / EcoDrift pump."""
    return {
        "SwitchON": 1,
        "PulseTide": 0,
        "FeedSwitch": 0,
        "TimerON": 0,
        "Mode": 1,
        "Linkage": 0,
        "Flow": 75,
        "Frequency": 50,
        "FeedTime": 10,
        "AutoMode": 0,
        "AutoFlow": 50,
        "AutoFreq": 50,
        "Fault_Overcurrent": 0,
        "Fault_Overvoltage": 0,
        "Fault_OverTemp": 0,
        "Fault_Undervoltage": 0,
        "Fault_Lockedrotor": 0,
        "Fault_no_liveload": 0,
        "Fault_UART": 0,
    }


def _default_attrs_dc_runner() -> dict[str, Any]:
    """Initial attribute state for a DC Runner return pump."""
    return {
        "SwitchON": 1,
        "FeedSwitch": 0,
        "Flow": 60,
        "Fault_Dry": 0,
        "Fault_Locked": 0,
        "Fault_Voltage": 0,
    }


def _default_attrs_dc_skimmer() -> dict[str, Any]:
    """Initial attribute state for the DC Runner series firmware.

    Applies to both the DC Skimmer and the DC Runner return pump — they share
    the same product_key and datapoint schema (verified against two independent
    real captures: dev_alias "Abschäumer" and "AQD_032A44"). Schedule blobs
    (AutoTimeNN, YMDData, HMSData) are intentionally omitted — the integration
    does not expose them.
    """
    return {
        "SwitchON": 1,
        "Mode": 1,  # 0: AP control, 1: Wireless control
        "FeedSwitch": 0,
        "TimerON": 0,
        "AutoMode": 1,  # 0: stop, 1: auto, 2: feeding
        "Motor_Speed": 60,
        "FeedTime": 10,
        "AutoGears": 50,
        "AutoFeedTime": 10,
        "Fault_Overcurrent": 0,
        "Fault_Overvoltage": 0,
        "Fault_OverTemp": 0,
        "Fault_Undervoltage": 0,
        "Fault_Lockedrotor": 0,
        "Fault_no_liveload": 0,
        "Fault_UART": 0,
    }


DEFAULT_ATTRS: dict[str, Any] = {
    "smartdrift": _default_attrs_smartdrift,
    "dc_runner": _default_attrs_dc_runner,
    # DC Runner return pump: same firmware as the skimmer, so reuse the rich
    # attribute defaults. Value differences (e.g. lower default motor speed
    # for a return pump) are cosmetic and can be overridden per instance.
    "dc_runner_return": _default_attrs_dc_skimmer,
    "dc_skimmer": _default_attrs_dc_skimmer,
}

# ── Datapoint schemas ─────────────────────────────────────────────────────────


def _datapoints_smartdrift() -> dict:
    """Gizwits datapoint schema for SmartDrift."""
    return {
        "entities": [
            {
                "display_name": "Main Control",
                "attrs": [
                    {
                        "name": "SwitchON",
                        "display_name": "Power Switch",
                        "type": "bool",
                        "rw": "rw",
                    },
                    {
                        "name": "PulseTide",
                        "display_name": "Wave Type",
                        "type": "bool",
                        "rw": "rw",
                    },
                    {
                        "name": "FeedSwitch",
                        "display_name": "Feeding Mode",
                        "type": "bool",
                        "rw": "rw",
                    },
                    {
                        "name": "TimerON",
                        "display_name": "Timer",
                        "type": "bool",
                        "rw": "rw",
                    },
                    {
                        "name": "Mode",
                        "display_name": "Wave Mode",
                        "type": "enum",
                        "rw": "rw",
                        "enum": ["随机造浪", "正弦波", "定频", "水流"],
                    },
                    {
                        "name": "Linkage",
                        "display_name": "Linkage",
                        "type": "enum",
                        "rw": "rw",
                        "enum": ["独立", "主机", "从机"],
                    },
                    {
                        "name": "Flow",
                        "display_name": "Flow Rate",
                        "type": "uint8",
                        "rw": "rw",
                        "min": 0,
                        "max": 100,
                        "unit": "%",
                    },
                    {
                        "name": "Frequency",
                        "display_name": "Frequency",
                        "type": "uint8",
                        "rw": "rw",
                        "min": 0,
                        "max": 100,
                        "unit": "%",
                    },
                    {
                        "name": "FeedTime",
                        "display_name": "Feeding Duration",
                        "type": "uint8",
                        "rw": "rw",
                        "min": 1,
                        "max": 60,
                        "unit": "min",
                    },
                ],
            },
            {
                "display_name": "Faults",
                "attrs": [
                    {
                        "name": "Fault_Overcurrent",
                        "display_name": "Overcurrent Fault",
                        "type": "bool",
                        "rw": "ro",
                    },
                    {
                        "name": "Fault_Overvoltage",
                        "display_name": "Overvoltage Fault",
                        "type": "bool",
                        "rw": "ro",
                    },
                    {
                        "name": "Fault_OverTemp",
                        "display_name": "Overtemperature Fault",
                        "type": "bool",
                        "rw": "ro",
                    },
                    {
                        "name": "Fault_Undervoltage",
                        "display_name": "Undervoltage Fault",
                        "type": "bool",
                        "rw": "ro",
                    },
                    {
                        "name": "Fault_Lockedrotor",
                        "display_name": "Locked Rotor Fault",
                        "type": "bool",
                        "rw": "ro",
                    },
                    {
                        "name": "Fault_no_liveload",
                        "display_name": "No Load Fault",
                        "type": "bool",
                        "rw": "ro",
                    },
                    {
                        "name": "Fault_UART",
                        "display_name": "UART Comm Fault",
                        "type": "bool",
                        "rw": "ro",
                    },
                ],
            },
        ]
    }


def _datapoints_dc_runner() -> dict:
    """Gizwits datapoint schema for a DC Runner return pump."""
    return {
        "entities": [
            {
                "display_name": "Main Control",
                "attrs": [
                    {
                        "name": "SwitchON",
                        "display_name": "Power Switch",
                        "type": "bool",
                        "rw": "rw",
                    },
                    {
                        "name": "FeedSwitch",
                        "display_name": "Feeding Mode",
                        "type": "bool",
                        "rw": "rw",
                    },
                    {
                        "name": "Flow",
                        "display_name": "Flow Speed",
                        "type": "uint8",
                        "rw": "rw",
                        "min": 30,
                        "max": 100,
                        "unit": "%",
                    },
                ],
            },
            {
                "display_name": "Faults",
                "attrs": [
                    {
                        "name": "Fault_Dry",
                        "display_name": "Dry Run Fault",
                        "type": "bool",
                        "rw": "ro",
                    },
                    {
                        "name": "Fault_Locked",
                        "display_name": "Rotor Blocked",
                        "type": "bool",
                        "rw": "ro",
                    },
                    {
                        "name": "Fault_Voltage",
                        "display_name": "Voltage Error",
                        "type": "bool",
                        "rw": "ro",
                    },
                ],
            },
        ]
    }


def _datapoints_dc_skimmer() -> dict:
    """Gizwits datapoint schema for a DC Skimmer (mirrors the real device)."""
    return {
        "entities": [
            {
                "display_name": "Main Control",
                "attrs": [
                    {
                        "name": "SwitchON",
                        "display_name": "Power Switch",
                        "type": "bool",
                        "rw": "rw",
                    },
                    {
                        "name": "Mode",
                        "display_name": "Control Source",
                        "type": "bool",
                        "rw": "rw",
                    },
                    {
                        "name": "FeedSwitch",
                        "display_name": "Feeding Mode",
                        "type": "bool",
                        "rw": "rw",
                    },
                    {
                        "name": "TimerON",
                        "display_name": "Timer",
                        "type": "bool",
                        "rw": "rw",
                    },
                    {
                        "name": "AutoMode",
                        "display_name": "Timer Mode",
                        "type": "enum",
                        "rw": "rw",
                        "enum": ["停机", "自动", "喂食"],
                    },
                    {
                        "name": "Motor_Speed",
                        "display_name": "Motor Speed",
                        "type": "uint8",
                        "rw": "rw",
                        # Device spec is 0-100; 0 stops the motor, running range 30-100.
                        "min": 0,
                        "max": 100,
                        "unit": "%",
                    },
                    {
                        "name": "FeedTime",
                        "display_name": "Feeding Duration",
                        "type": "uint8",
                        "rw": "rw",
                        "min": 1,
                        "max": 60,
                        "unit": "min",
                    },
                    {
                        "name": "AutoGears",
                        "display_name": "Timer Speed",
                        "type": "uint8",
                        "rw": "rw",
                        "min": 0,
                        "max": 100,
                        "unit": "%",
                    },
                    {
                        "name": "AutoFeedTime",
                        "display_name": "Timer Feeding Time",
                        "type": "uint8",
                        "rw": "rw",
                        "min": 1,
                        "max": 60,
                        "unit": "min",
                    },
                ],
            },
            {
                "display_name": "Faults",
                "attrs": [
                    {
                        "name": "Fault_Overcurrent",
                        "display_name": "Overcurrent Fault",
                        "type": "bool",
                        "rw": "ro",
                    },
                    {
                        "name": "Fault_Overvoltage",
                        "display_name": "Overvoltage Fault",
                        "type": "bool",
                        "rw": "ro",
                    },
                    {
                        "name": "Fault_OverTemp",
                        "display_name": "Overtemperature Fault",
                        "type": "bool",
                        "rw": "ro",
                    },
                    {
                        "name": "Fault_Undervoltage",
                        "display_name": "Undervoltage Fault",
                        "type": "bool",
                        "rw": "ro",
                    },
                    {
                        "name": "Fault_Lockedrotor",
                        "display_name": "Locked Rotor Fault",
                        "type": "bool",
                        "rw": "ro",
                    },
                    {
                        "name": "Fault_no_liveload",
                        "display_name": "No Load Fault",
                        "type": "bool",
                        "rw": "ro",
                    },
                    {
                        "name": "Fault_UART",
                        "display_name": "UART Comm Fault",
                        "type": "bool",
                        "rw": "ro",
                    },
                ],
            },
        ]
    }


DATAPOINTS: dict[str, Any] = {
    SMARTDRIFT_PRODUCT_KEY: _datapoints_smartdrift,
    DC_RUNNER_PRODUCT_KEY: _datapoints_dc_runner,
    DC_SKIMMER_PRODUCT_KEY: _datapoints_dc_skimmer,
}

# ── Virtual device registry ───────────────────────────────────────────────────


class VirtualDevice:
    """Represents a single simulated Gizwits device."""

    def __init__(self, device_type: str, index: int) -> None:
        self.device_type = device_type
        self.did = f"{device_type[:4].upper()}-{str(uuid.uuid4())[:8].upper()}"
        self.product_key = PRODUCT_KEYS[device_type]
        self.product_name = PRODUCT_NAMES[device_type]
        self.alias = f"Aqua Medic {device_type.replace('_', ' ').title()} #{index + 1}"
        self.is_online = True
        self.attrs: dict[str, Any] = DEFAULT_ATTRS[device_type]()
        self.updated_at = int(time.time())

    def to_binding(self) -> dict:
        """Return the device representation for /app/bindings."""
        return {
            "did": self.did,
            "product_key": self.product_key,
            "product_name": self.product_name,
            "dev_alias": self.alias,
            "is_online": self.is_online,
            "mac": f"AA:BB:CC:{self.did[:2]}:{self.did[2:4]}:{self.did[4:6]}",
        }

    def to_latest(self) -> dict:
        """Return the device data representation for /app/devdata/<did>/latest."""
        return {
            "did": self.did,
            "attr": dict(self.attrs),
            "updated_at": self.updated_at,
        }

    def update_attrs(self, attrs: dict[str, Any]) -> None:
        """Apply a control payload to the device state."""
        for key, value in attrs.items():
            if key in self.attrs:
                self.attrs[key] = value
                log.info("  [%s] %s → %s", self.alias, key, value)
            else:
                log.warning("  [%s] unknown attr '%s' — ignored", self.alias, key)
        self.updated_at = int(time.time())

    def toggle_online(self) -> None:
        self.is_online = not self.is_online
        log.info("[%s] is_online → %s", self.alias, self.is_online)


# ── Simulator state ───────────────────────────────────────────────────────────


class SimulatorState:
    """Global state shared by all request handlers."""

    def __init__(self, config: dict) -> None:
        self.username: str = config["username"]
        self.password: str = config["password"]

        # Build virtual device list
        self.devices: dict[str, VirtualDevice] = {}
        counts: dict[str, int] = {}
        for entry in config.get("devices", []):
            dtype = entry["type"].lower()
            if dtype not in PRODUCT_KEYS:
                log.warning("Unknown device type '%s' — skipped", dtype)
                continue
            for i in range(entry.get("count", 1)):
                idx = counts.get(dtype, 0)
                dev = VirtualDevice(dtype, idx)
                self.devices[dev.did] = dev
                counts[dtype] = idx + 1
                log.info("  Registered: %s  (did=%s)", dev.alias, dev.did)

        # Active tokens: token → username
        self._tokens: dict[str, str] = {}

    # ── Auth helpers ──────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> dict | None:
        """Validate credentials; return token payload or None."""
        if username == self.username and password == self.password:
            token = str(uuid.uuid4()).replace("-", "")
            uid = str(uuid.uuid4()).replace("-", "")
            self._tokens[token] = username
            log.info("LOGIN  %s  →  token %s…", username, token[:8])
            return {"token": token, "uid": uid, "expire_at": int(time.time()) + 86400}
        log.warning("LOGIN FAILED  user=%s", username)
        return None

    def is_authenticated(self, token: str | None) -> bool:
        return token is not None and token in self._tokens

    def get_device(self, did: str) -> VirtualDevice | None:
        return self.devices.get(did)

    def all_bindings(self) -> list[dict]:
        return [d.to_binding() for d in self.devices.values()]

    def datapoints_for(self, product_key: str) -> dict | None:
        factory = DATAPOINTS.get(product_key)
        return factory() if factory else None


# ── HTTP request handler ──────────────────────────────────────────────────────


class GizwitsHandler(BaseHTTPRequestHandler):
    """Handles all Gizwits API requests."""

    # Injected by GizwitsServer
    state: SimulatorState

    # ── Logging ───────────────────────────────────────────────────────────────

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default BaseHTTPRequestHandler output."""

    def _log(self, method: str, status: int, extra: str = "") -> None:
        msg = f"{method:6}  {self.path}  →  {status}"
        if extra:
            msg += f"  ({extra})"
        log.info(msg)

    # ── Response helpers ──────────────────────────────────────────────────────

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: int, message: str) -> None:
        self._send_json({"error_code": status, "msg": message}, status)

    def _read_json(self) -> dict | None:
        length = self.headers.get("Content-Length")
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(int(length)))
        except (json.JSONDecodeError, ValueError):
            return None

    def _token(self) -> str | None:
        return self.headers.get("X-Gizwits-User-token")

    # ── Path parsing ──────────────────────────────────────────────────────────

    def _path_no_query(self) -> str:
        return self.path.split("?")[0].rstrip("/") or "/"

    # ── Route dispatcher ──────────────────────────────────────────────────────

    def do_GET(self) -> None:
        path = self._path_no_query()

        # GET /app/bindings
        if path == "/app/bindings":
            if not self.state.is_authenticated(self._token()):
                self._log("GET", 401)
                self._send_error(401, "Unauthorized")
                return
            devices = self.state.all_bindings()
            self._send_json({"devices": devices, "total": len(devices)})
            self._log("GET", 200, f"{len(devices)} device(s)")
            return

        # GET /app/devdata/<did>/latest
        if path.startswith("/app/devdata/") and path.endswith("/latest"):
            if not self.state.is_authenticated(self._token()):
                self._send_error(401, "Unauthorized")
                return
            did = path.split("/")[3]
            dev = self.state.get_device(did)
            if dev is None:
                self._log("GET", 404, f"did={did}")
                self._send_error(404, "Device not found")
                return
            self._send_json(dev.to_latest())
            self._log("GET", 200, f"did={did}  attrs={list(dev.attrs.keys())[:4]}…")
            return

        # GET /app/datapoint?product_key=<pk>
        if path == "/app/datapoint":
            if not self.state.is_authenticated(self._token()):
                self._send_error(401, "Unauthorized")
                return
            pk = (
                self.path.split("product_key=")[-1].split("&")[0]
                if "product_key=" in self.path
                else ""
            )
            schema = self.state.datapoints_for(pk)
            if schema is None:
                self._send_error(404, f"No datapoints for product_key={pk}")
                self._log("GET", 404, f"product_key={pk}")
                return
            self._send_json(schema)
            self._log("GET", 200, f"product_key={pk[:8]}…")
            return

        self._send_error(404, "Not found")
        self._log("GET", 404)

    def do_POST(self) -> None:
        path = self._path_no_query()

        # POST /app/provision  → always OK, no state needed
        if path == "/app/provision":
            self._send_json({"is_new": False})
            self._log("POST", 200, "provision ok")
            return

        # POST /app/login
        if path == "/app/login":
            body = self._read_json()
            if body is None:
                self._send_error(400, "Invalid JSON")
                return
            result = self.state.login(
                body.get("username", ""), body.get("password", "")
            )
            if result:
                self._send_json(result)
                self._log("POST", 200, "login ok")
            else:
                self._send_error(400, "username or password error")
                self._log("POST", 400, "bad credentials")
            return

        # POST /app/control/<did>
        if path.startswith("/app/control/"):
            if not self.state.is_authenticated(self._token()):
                self._send_error(401, "Unauthorized")
                return
            did = path.split("/")[3]
            dev = self.state.get_device(did)
            if dev is None:
                self._send_error(404, "Device not found")
                self._log("POST", 404, f"did={did}")
                return
            body = self._read_json()
            if body is None:
                self._send_error(400, "Invalid JSON")
                return
            attrs = body.get("attrs", {})
            if attrs:
                dev.update_attrs(attrs)
            self._send_json({"success": True})
            self._log("POST", 200, f"control did={did}")
            return

        self._send_error(404, "Not found")
        self._log("POST", 404)


# ── Server wiring ─────────────────────────────────────────────────────────────


class GizwitsServer(HTTPServer):
    """HTTP server with injected simulator state."""

    def __init__(
        self,
        server_address: tuple[str, int],
        state: SimulatorState,
    ) -> None:
        self.state = state
        # Inject state into the handler class via a closure
        handler = self._make_handler(state)
        super().__init__(server_address, handler)

    @staticmethod
    def _make_handler(state: SimulatorState) -> type[GizwitsHandler]:
        """Return a GizwitsHandler subclass with `state` bound."""

        class BoundHandler(GizwitsHandler):
            pass

        BoundHandler.state = state
        return BoundHandler


# ── IP management ─────────────────────────────────────────────────────────────


def detect_default_interface() -> str:
    """Best-effort detection of the primary network interface.

    Reads the default route (``ip route show default``) and returns the device
    after ``dev``. Falls back to ``eth0`` if detection fails.
    """
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            check=False,
        )
        parts = result.stdout.split()
        if "dev" in parts:
            return parts[parts.index("dev") + 1]
    except (OSError, ValueError, IndexError):
        pass
    return "eth0"


def ensure_virtual_ip(ip: str, interface: str) -> None:
    """Add a virtual IP alias on *interface* if not already present."""
    result = subprocess.run(
        ["ip", "addr", "show", "dev", interface], capture_output=True, text=True
    )
    if f"inet {ip}" in result.stdout:
        log.info("Virtual IP %s already present on %s", ip, interface)
        return
    log.info("Adding virtual IP %s/24 on %s…", ip, interface)
    subprocess.run(["ip", "addr", "add", f"{ip}/24", "dev", interface], check=True)
    time.sleep(1)


def remove_virtual_ip(ip: str, interface: str) -> None:
    """Remove the virtual IP alias from *interface*."""
    subprocess.run(
        ["ip", "addr", "del", f"{ip}/24", "dev", interface], capture_output=True
    )
    log.info("Virtual IP %s removed from %s", ip, interface)


# ── Entrypoint ────────────────────────────────────────────────────────────────


def main() -> None:
    parser = OptionParser(usage="sudo %prog [-c <config_file>]", version="1.0.0")
    parser.add_option("-c", "--config", dest="config", help="Path to JSON config file")
    parser.add_option(
        "-i",
        "--interface",
        dest="interface",
        help="Network interface for the virtual IP (overrides config; "
        "default: auto-detect, falling back to eth0)",
    )
    (options, _) = parser.parse_args()

    if os.geteuid() != 0:
        print("ERROR: Must be run as root (needed to add virtual IP)")
        parser.print_usage()
        sys.exit(1)

    exec_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    conf_path = options.config or os.path.join(exec_dir, "gizwits_sim_config.json")

    log.info("Loading config from %s", conf_path)
    with open(conf_path, encoding="utf-8") as f:
        config = json.load(f)

    virtual_ip = config.get("virtual_ip", "127.0.0.1")
    port = config.get("port", 8080)

    # Interface resolution: CLI flag > config key > auto-detected default route.
    interface = (
        options.interface or config.get("interface") or detect_default_interface()
    )

    # Register virtual IP
    if virtual_ip != "127.0.0.1":
        ensure_virtual_ip(virtual_ip, interface)

    # Build simulator state
    state = SimulatorState(config)

    log.info("")
    log.info("═══════════════════════════════════════════════════")
    log.info("  Gizwits Simulator")
    log.info("  Listening on  http://%s:%d", virtual_ip, port)
    if virtual_ip != "127.0.0.1":
        log.info("  Interface: %s", interface)
    log.info("  Username: %s  |  Password: %s", state.username, state.password)
    log.info("  Devices: %d registered", len(state.devices))
    for dev in state.devices.values():
        log.info("    • %s  (did=%s  pk=%s…)", dev.alias, dev.did, dev.product_key[:8])
    log.info("═══════════════════════════════════════════════════")
    log.info("")
    log.info("Tip: To point the integration at this simulator, add to")
    log.info("     your HA configuration.yaml or patch const.py URLs.")
    log.info("")

    server = GizwitsServer((virtual_ip, port), state)

    try:
        log.info("Press Ctrl-C to stop")
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down…")
        server.shutdown()
    finally:
        if virtual_ip != "127.0.0.1":
            remove_virtual_ip(virtual_ip, interface)
        log.info("Bye!")


if __name__ == "__main__":
    main()
