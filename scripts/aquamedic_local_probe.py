#!/usr/bin/env python3
"""Read an Aqua Medic pump over the local network (Gizwits LAN protocol).

Probe to check that local access works on a pump, and to compare what it
reports locally with what the cloud integration shows. Read-only unless you
ask for a write explicitly (see below). No Home Assistant, no account,
standard library only.

What it does:
  1. finds the pump (UDP 12414: broadcast, or straight to --host);
  2. asks the pump for its passcode and logs in (TCP 12416);
  3. reads the full status block and decodes it with the datapoint schema of
     the pump's product (scripts/devices_datapoints/*_<product key>.json, or
     the public Gizwits schema when the file is not there);
  4. with --watch SECONDS, keeps the session open and prints every change the
     pump pushes (change a value in the Aqua Medic app to see it appear).

Usage:
  python3 scripts/aquamedic_local_probe.py                  # discover, read once
  python3 scripts/aquamedic_local_probe.py --host 192.168.1.50
  python3 scripts/aquamedic_local_probe.py --host 192.168.1.50 --watch 120
  python3 scripts/aquamedic_local_probe.py --json > status.json

Writes (one change at a time, each one checked against what the pump reports):
  --write-test              harmless round trip: feed pause duration +1 min,
                            checked on the pump, then put back
  --set NAME=VALUE          show what would be sent (dry run), e.g. --set Flow=40
  --set NAME=VALUE --apply  really send it
Only controls confirmed on a real EcoDrift 8.3 by the aquamedic-local project
are accepted: SwitchON PulseTide FeedSwitch TimerON Mode Linkage Flow Frequency
FeedTime. A flow write always carries the current frequency, because the
firmware ignores a write that changes the flow alone. These pumps keep a tank
alive: do not switch SwitchON off or change the flow unless you mean to.

If the pump says it is "not in binding mode", power-cycle it (or press its
Wi-Fi button briefly) and run the script again within a few minutes.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import socket
import struct
import sys
import time
import urllib.request
from typing import Any

HEADER = b"\x00\x00\x00\x03"
UDP_PORT = 12414
TCP_PORT = 12416

CMD_DISCOVER = 0x0003
CMD_DISCOVER_REPLY = 0x0004
CMD_PASSCODE_REQ = 0x0006
CMD_PASSCODE_RESP = 0x0007
CMD_LOGIN_REQ = 0x0008
CMD_LOGIN_RESP = 0x0009
CMD_PING = 0x0015
CMD_PONG = 0x0016
# Status packets: 0x0091 / 0x0093 (pushed by the pump) and 0x0094 (reply to a read).
CMD_P0_SEND = 0x0093
P0_COMMANDS = (0x0091, 0x0093, 0x0094)
ACTION_WRITE = 0x01
ACTION_READ = 0x02
ACTION_READ_REPLY = 0x03
ACTION_REPORT = 0x04

# Controls confirmed on a real pump by the aquamedic-local project (EcoDrift 8.3,
# module 04020B25): name -> allowed values (None = on/off, tuple = (min, max),
# "enum" = a number or one of the labels of the schema).
SAFE_WRITES: dict[str, Any] = {
    "SwitchON": None,
    "PulseTide": None,
    "FeedSwitch": None,
    "TimerON": None,
    "Mode": "enum",
    "Linkage": "enum",
    "Flow": (0, 100),
    "Frequency": (0, 100),
    "FeedTime": (1, 60),
}
# Written together with the key, at its current value (see the module docstring).
COMPANIONS = {"Flow": "Frequency"}

SCHEDULE_PREFIX = "AutoTime"
EMPTY_BYTE = 0xEE  # filler of an unused timer slot

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_GLOB = os.path.join(SCRIPT_DIR, "devices_datapoints", "*_{product_key}.json")
PUBLIC_SCHEMA_URL = "https://euapi.gizwits.com/app/datapoint?product_key={product_key}"

# Enum labels of the public schema are Chinese: translate the ones we know.
ENUM_LABELS = {
    "经典造浪": "classic_wave",
    "正弦造浪": "sine_wave",
    "随机造浪": "random_wave",
    "恒流造浪": "constant_flow",
    "独立": "independent",
    "主机": "master",
    "从机": "slave",
    "停机": "stop",
    "自动": "auto",
    "喂食": "feeding",
}


class ProbeError(Exception):
    """Something went wrong talking to the pump."""


# ── Framing ───────────────────────────────────────────────────────────────────


def _varint(number: int) -> bytes:
    out = bytearray()
    while True:
        byte = number & 0x7F
        number >>= 7
        out.append(byte | 0x80 if number else byte)
        if not number:
            return bytes(out)


def build_packet(cmd: int, payload: bytes = b"") -> bytes:
    """Packet: header | varint length | flag 00 | command | payload."""
    body = b"\x00" + struct.pack(">H", cmd) + payload
    return HEADER + _varint(len(body)) + body


def _split(data: bytes) -> tuple[int, bytes, int] | None:
    """First complete packet of *data* as (command, payload, bytes used)."""
    if len(data) < 5 or data[:4] != HEADER:
        return None
    length, shift, i = 0, 0, 4
    while True:
        if i >= len(data):
            return None
        byte = data[i]
        i += 1
        length |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            break
        if shift > 28:
            raise ProbeError("bad packet length")
    if length < 3 or len(data) < i + length:
        return None
    body = data[i : i + length]
    return struct.unpack(">H", body[1:3])[0], body[3:], i + length


class Stream:
    """Reassembles packets from a TCP stream."""

    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        self._buf = b""

    def packets(self, timeout: float) -> list[tuple[int, bytes]]:
        """Wait up to *timeout* s for data and return every packet complete so far."""
        self._sock.settimeout(timeout)
        try:
            chunk = self._sock.recv(4096)
        except TimeoutError:
            return []
        if not chunk:
            raise ProbeError("the pump closed the connection")
        self._buf += chunk
        out: list[tuple[int, bytes]] = []
        while True:
            if self._buf[:4] != HEADER[: min(4, len(self._buf))]:
                idx = self._buf.find(HEADER, 1)
                self._buf = self._buf[idx:] if idx > 0 else b""
                if not self._buf:
                    break
            found = _split(self._buf)
            if found is None:
                break
            cmd, payload, used = found
            self._buf = self._buf[used:]
            out.append((cmd, payload))
        return out


def _lv_fields(payload: bytes) -> list[bytes]:
    out, i = [], 0
    while i + 2 <= len(payload):
        size = struct.unpack(">H", payload[i : i + 2])[0]
        i += 2
        out.append(payload[i : i + size])
        i += size
    return out


# ── Discovery ─────────────────────────────────────────────────────────────────


def discover(host: str | None, wait: float) -> list[dict[str, str]]:
    """Find pumps: unicast to *host*, or broadcast on the local network."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.5)
    target = host or "255.255.255.255"
    found: dict[str, dict[str, str]] = {}
    deadline = time.monotonic() + wait
    next_send = 0.0
    try:
        while time.monotonic() < deadline:
            if time.monotonic() >= next_send:
                sock.sendto(build_packet(CMD_DISCOVER), (target, UDP_PORT))
                next_send = time.monotonic() + 1.0
            try:
                data, (ip, _port) = sock.recvfrom(2048)
            except TimeoutError:
                continue
            parsed = _split(data)
            if parsed is None or parsed[0] != CMD_DISCOVER_REPLY:
                continue
            fields = _lv_fields(parsed[1])
            if len(fields) < 4 or len(fields[3]) != 32:
                continue
            found[ip] = {
                "ip": ip,
                "did": fields[0].decode("ascii", "replace"),
                "mac": fields[1].hex(":"),
                "firmware": fields[2].decode("ascii", "replace"),
                "product_key": fields[3].decode("ascii", "replace"),
            }
            if host:
                break
    finally:
        sock.close()
    return list(found.values())


# ── Datapoint schema ──────────────────────────────────────────────────────────


class Schema:
    """Layout of the status block, from a Gizwits datapoint file."""

    def __init__(self, document: dict[str, Any]) -> None:
        datapoints = document.get("datapoints", document)
        self.name = datapoints.get("name", "?")
        self.attrs: list[dict[str, Any]] = datapoints["entities"][0]["attrs"]
        self.length = max(self._end(a) for a in self.attrs)
        self.by_name = {a["name"]: a for a in self.attrs}
        writable = [a for a in self.attrs if a.get("type") == "status_writable"]
        self.write_length = max(self._end(a) for a in writable)
        # One flag bit per datapoint id, big-endian, in the smallest whole number of bytes.
        self.flag_bytes = (max(a["id"] for a in writable) + 8) // 8
        # Bit fields sharing a byte offset form one big-endian word whose
        # bit 0 is the least significant bit (same convention as the app).
        self._words: dict[int, int] = {}
        for attr in self.attrs:
            pos = attr["position"]
            if pos["unit"] == "bit":
                size = (pos["bit_offset"] + pos["len"] + 7) // 8
                self._words[pos["byte_offset"]] = max(
                    self._words.get(pos["byte_offset"], 0), size
                )

    @staticmethod
    def _end(attr: dict[str, Any]) -> int:
        pos = attr["position"]
        if pos["unit"] == "bit":
            return pos["byte_offset"] + (pos["bit_offset"] + pos["len"] + 7) // 8
        return pos["byte_offset"] + pos["len"]

    def raw(self, status: bytes) -> dict[str, Any]:
        """Every datapoint as a bool, an int, or a hex string (binary ones)."""
        if len(status) < self.length:
            raise ProbeError(f"status too short: {len(status)} < {self.length}")
        out: dict[str, Any] = {}
        for attr in self.attrs:
            pos = attr["position"]
            offset = pos["byte_offset"]
            kind = attr["data_type"]
            if pos["unit"] == "bit":
                word = int.from_bytes(
                    status[offset : offset + self._words[offset]], "big"
                )
                value = (word >> pos["bit_offset"]) & ((1 << pos["len"]) - 1)
                out[attr["name"]] = bool(value) if kind == "bool" else value
            elif kind == "binary":
                out[attr["name"]] = status[offset : offset + pos["len"]].hex()
            else:
                out[attr["name"]] = int.from_bytes(
                    status[offset : offset + pos["len"]], "big"
                )
        return out

    def decode(self, status: bytes) -> dict[str, Any]:
        """Like raw(), with the enum values shown as "label (number)"."""
        out = self.raw(status)
        for attr in self.attrs:
            labels = attr.get("enum")
            value = out[attr["name"]]
            if attr["data_type"] == "enum" and labels and value < len(labels):
                out[attr["name"]] = (
                    f"{ENUM_LABELS.get(labels[value], labels[value])} ({value})"
                )
        return out

    def enum_value(self, name: str, text: str) -> int:
        """Number of an enum value given as a number or as a label."""
        labels = [
            str(ENUM_LABELS.get(x, x)) for x in self.by_name[name].get("enum", [])
        ]
        if text.isdigit() and int(text) < len(labels):
            return int(text)
        if text in labels:
            return labels.index(text)
        raise ProbeError(f"{name}: {text!r} is not one of {', '.join(labels)}")

    def encode_write(self, base: bytes, changes: dict[str, int]) -> tuple[bytes, bytes]:
        """Flags and data of a write that changes only *changes*.

        The data block starts from the last status, so everything else keeps
        its current value.
        """
        data = bytearray(base[: self.write_length])
        flags = 0
        for name, value in changes.items():
            attr = self.by_name[name]
            pos = attr["position"]
            offset = pos["byte_offset"]
            flags |= 1 << attr["id"]
            if pos["unit"] == "bit":
                size = self._words[offset]
                word = int.from_bytes(data[offset : offset + size], "big")
                mask = ((1 << pos["len"]) - 1) << pos["bit_offset"]
                word = (word & ~mask) | ((int(value) << pos["bit_offset"]) & mask)
                data[offset : offset + size] = word.to_bytes(size, "big")
            else:
                data[offset : offset + pos["len"]] = int(value).to_bytes(
                    pos["len"], "big"
                )
        return flags.to_bytes(self.flag_bytes, "big"), bytes(data)


def load_schema(product_key: str, path: str | None) -> Schema:
    """Schema from --datapoints, the repository captures, or the public Gizwits one."""
    candidates = (
        [path]
        if path
        else sorted(glob.glob(SCHEMA_GLOB.format(product_key=product_key)))
    )
    for candidate in candidates:
        with open(candidate, encoding="utf-8") as handle:
            return Schema(json.load(handle))
    url = PUBLIC_SCHEMA_URL.format(product_key=product_key)
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return Schema(json.load(response))
    except Exception as exc:
        raise ProbeError(
            f"no datapoint file for product {product_key} and the public schema "
            f"could not be fetched ({exc}); pass one with --datapoints"
        ) from exc


# ── Session ───────────────────────────────────────────────────────────────────


def status_from_packet(cmd: int, payload: bytes, length: int) -> bytes | None:
    """Status block carried by a P0 packet, whatever the exact header shape.

    The status is the last *length* bytes, preceded by the action byte
    (0x03 read reply, 0x04 report).
    """
    if cmd not in P0_COMMANDS or len(payload) < length + 1:
        return None
    if payload[-length - 1] in (ACTION_READ_REPLY, ACTION_REPORT):
        return payload[-length:]
    return None


class Session:
    """One logged-in TCP session with a pump."""

    def __init__(self, host: str, timeout: float) -> None:
        self._timeout = timeout
        self._sock = socket.create_connection((host, TCP_PORT), timeout=timeout)
        self._stream = Stream(self._sock)
        self._sn = 0
        self.passcode = ""

    def close(self) -> None:
        self._sock.close()

    def _wait_for(self, cmd: int) -> bytes:
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            for got, payload in self._stream.packets(0.5):
                if got == cmd:
                    return payload
        raise ProbeError(f"no answer (command 0x{cmd:04x}) from the pump")

    def login(self) -> None:
        self._sock.sendall(build_packet(CMD_PASSCODE_REQ))
        payload = self._wait_for(CMD_PASSCODE_RESP)
        size = struct.unpack(">H", payload[:2])[0] if len(payload) >= 2 else 0
        self.passcode = payload[2 : 2 + size].decode("ascii", "replace")
        if not self.passcode:
            raise ProbeError(
                "the pump gave no passcode (not in binding mode): power-cycle it, "
                "or press its Wi-Fi button briefly, and retry within a few minutes"
            )
        code = self.passcode.encode()
        self._sock.sendall(
            build_packet(CMD_LOGIN_REQ, struct.pack(">H", len(code)) + code)
        )
        if self._wait_for(CMD_LOGIN_RESP)[:1] != b"\x00":
            raise ProbeError("login refused by the pump")

    def request_status(self) -> None:
        self._sn += 1
        payload = struct.pack(">I", self._sn) + bytes([ACTION_READ])
        self._sock.sendall(build_packet(CMD_P0_SEND, payload))

    def write(self, flags: bytes, data: bytes) -> None:
        self._sn += 1
        payload = struct.pack(">I", self._sn) + bytes([ACTION_WRITE]) + flags + data
        self._sock.sendall(build_packet(CMD_P0_SEND, payload))

    def ping(self) -> None:
        self._sock.sendall(build_packet(CMD_PING))

    def poll(self, timeout: float, length: int) -> list[bytes]:
        """Status blocks received within *timeout* s (pushed or answered)."""
        out = []
        for cmd, payload in self._stream.packets(timeout):
            status = status_from_packet(cmd, payload, length)
            if status is not None:
                out.append(status)
        return out

    def read_status(self, length: int) -> bytes:
        self.request_status()
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            blocks = self.poll(0.5, length)
            if blocks:
                return blocks[-1]
        raise ProbeError(f"no status of {length} bytes received")


# ── Writes ────────────────────────────────────────────────────────────────────


def parse_assignment(schema: Schema, text: str) -> tuple[str, int]:
    """ "Flow=40" -> ("Flow", 40), checked against the confirmed controls."""
    name, sep, raw = text.partition("=")
    name, raw = name.strip(), raw.strip()
    if not sep or name not in SAFE_WRITES:
        raise ProbeError(
            f"{text!r}: use NAME=VALUE with NAME in {', '.join(SAFE_WRITES)}"
        )
    spec = SAFE_WRITES[name]
    if spec is None:
        if raw.lower() not in ("1", "0", "on", "off", "true", "false"):
            raise ProbeError(f"{name}: expected on/off, got {raw!r}")
        return name, 1 if raw.lower() in ("1", "on", "true") else 0
    if spec == "enum":
        return name, schema.enum_value(name, raw)
    low, high = spec
    try:
        number = int(raw)
    except ValueError as exc:
        raise ProbeError(f"{name}: expected a number, got {raw!r}") from exc
    if not low <= number <= high:
        raise ProbeError(f"{name}: {number} is outside {low}-{high}")
    return name, number


SETTLE_SECONDS = 4.0


def apply_change(
    session: Session,
    schema: Schema,
    status: bytes,
    changes: dict[str, int],
    timeout: float,
) -> bytes:
    """Send one write, wait for the pump to report it, then check it held.

    The first report can be an echo of the command: some values are rewritten
    by the pump a few seconds later (the flow while the timer is on). So the
    status is read again after a short wait, and a value that went back is an
    error.
    """
    changes = dict(changes)
    current = schema.raw(status)
    for name, companion in COMPANIONS.items():
        if name in changes and companion not in changes:
            changes[companion] = current[companion]
    flags, data = schema.encode_write(status, changes)
    session.write(flags, data)
    shown = ", ".join(f"{n}={v}" for n, v in changes.items())
    deadline = time.monotonic() + timeout
    confirmed = None
    while confirmed is None and time.monotonic() < deadline:
        for block in session.poll(0.5, schema.length):
            reported = schema.raw(block)
            if all(int(reported[name]) == value for name, value in changes.items()):
                confirmed = block
    if confirmed is None:
        raise ProbeError(
            f"the pump did not report {shown} within {timeout:g} s (write not applied?)"
        )
    time.sleep(SETTLE_SECONDS)
    later = session.read_status(schema.length)
    kept = schema.raw(later)
    back = {n: kept[n] for n, v in changes.items() if int(kept[n]) != v}
    if back:
        went = ", ".join(f"{n}={v}" for n, v in back.items())
        raise ProbeError(
            f"the pump accepted {shown} but reports {went} {SETTLE_SECONDS:g} s later: "
            "it rewrote the value (timer on? fault active?)"
        )
    return later


def run_writes(
    session: Session, schema: Schema, status: bytes, args: argparse.Namespace, log: Any
) -> bytes:
    if args.write_test:
        before = schema.raw(status)["FeedTime"]
        probe = before + 1 if before < 60 else before - 1
        log(f"\nWrite test: FeedTime {before} -> {probe} -> {before}")
        status = apply_change(
            session, schema, status, {"FeedTime": probe}, args.timeout
        )
        log(
            f"  pump reports FeedTime={schema.raw(status)['FeedTime']} and keeps it: the write works"
        )
        status = apply_change(
            session, schema, status, {"FeedTime": before}, args.timeout
        )
        log(f"  restored, pump reports FeedTime={schema.raw(status)['FeedTime']}")
    if args.set:
        changes = dict(parse_assignment(schema, item) for item in args.set)
        current = schema.raw(status)
        for name, value in changes.items():
            log(f"\n{name}: {current[name]} -> {value}")
        if not args.apply:
            log("Dry run: nothing sent. Add --apply to send it.")
        else:
            status = apply_change(session, schema, status, changes, args.timeout)
            log(
                f"Done: the pump reports the new value and kept it {SETTLE_SECONDS:g} s later."
            )
    return status


# ── Display ───────────────────────────────────────────────────────────────────


def decode_slot(raw: bytes) -> dict[str, Any] | None:
    """One timer slot (6 bytes DC Runner, 8 bytes EcoDrift / SmartDrift)."""
    if not any(raw) or raw[0] == EMPTY_BYTE:
        return None
    start = raw[0] * 60 + raw[1]
    end = raw[2] * 60 + raw[3]
    slot: dict[str, Any] = {
        "start": f"{raw[0]:02d}:{raw[1]:02d}",
        "end": f"{raw[2]:02d}:{raw[3]:02d}",
        "mode": raw[4],
        "value": raw[5],
    }
    if len(raw) == 8:
        slot["frequency"] = raw[6]
        slot["tide"] = bool(raw[7])
    if start == end:
        slot["note"] = "whole day" if start == 0 else "zero-length window"
    return slot


def schedule_of(values: dict[str, Any]) -> list[dict[str, Any]]:
    slots = []
    for name, value in values.items():
        if name.startswith(SCHEDULE_PREFIX):
            slot = decode_slot(bytes.fromhex(value))
            if slot is not None:
                slots.append({"slot": int(name[len(SCHEDULE_PREFIX) :]), **slot})
    return slots


def print_report(info: dict[str, str], values: dict[str, Any], status: bytes) -> None:
    print(f"Pump        {info['ip']}  did={info['did']}  mac={info['mac']}")
    print(f"Firmware    {info['firmware']}")
    print(f"Product     {info['product_key']}")
    print(f"Status      {len(status)} bytes")
    print()
    print("Datapoints (same names as the cloud attributes):")
    for name, value in values.items():
        if not name.startswith(SCHEDULE_PREFIX):
            print(f"  {name:<20} {value}")
    schedule = schedule_of(values)
    print()
    print(
        f"Timer slots in use: {len(schedule)} of {sum(n.startswith(SCHEDULE_PREFIX) for n in values)}"
    )
    for slot in schedule:
        print("  " + "  ".join(f"{k}={v}" for k, v in slot.items()))


def print_changes(old: dict[str, Any], new: dict[str, Any]) -> None:
    stamp = time.strftime("%H:%M:%S")
    changed = [k for k in new if old.get(k) != new[k]]
    if not changed:
        print(f"{stamp}  status pushed, nothing changed")
    for name in changed:
        print(f"{stamp}  {name}: {old.get(name)} -> {new[name]}")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument(
        "--host", help="IP address of the pump (default: discover on the LAN)"
    )
    parser.add_argument(
        "--watch",
        type=float,
        default=0,
        metavar="SECONDS",
        help="stay connected and print the changes the pump pushes",
    )
    parser.add_argument("--datapoints", help="datapoint JSON file of the product")
    parser.add_argument(
        "--timeout", type=float, default=5.0, help="network timeout in seconds"
    )
    parser.add_argument(
        "--json", action="store_true", help="print the decoded status as JSON"
    )
    parser.add_argument(
        "--write-test",
        action="store_true",
        help="harmless write test: feed pause duration +1 min, checked, then restored",
    )
    parser.add_argument(
        "--set",
        action="append",
        metavar="NAME=VALUE",
        help="change a confirmed control (dry run unless --apply)",
    )
    parser.add_argument(
        "--apply", action="store_true", help="really send the --set changes"
    )
    args = parser.parse_args()

    log = (lambda *a: print(*a, file=sys.stderr)) if args.json else print

    try:
        log(f"Looking for the pump ({args.host or 'broadcast'})...")
        pumps = discover(args.host, max(args.timeout, 3.0))
        if not pumps:
            raise ProbeError(
                "no pump answered on UDP 12414. Give its address with --host, and check "
                "that the pump and this machine can reach each other (routed VLANs are fine)"
            )
        if len(pumps) > 1 and not args.host:
            log("Several pumps answered; using the first. Use --host to pick one:")
            for pump in pumps:
                log(f"  {pump['ip']}  {pump['did']}  {pump['product_key']}")
        info = pumps[0]

        schema = load_schema(info["product_key"], args.datapoints)
        log(f"Schema      {schema.name}, status of {schema.length} bytes")

        session = Session(info["ip"], args.timeout)
        try:
            session.login()
            status = session.read_status(schema.length)
            values = schema.decode(status)
            if args.json:
                print(
                    json.dumps(
                        {
                            **info,
                            "status_hex": status.hex(),
                            "values": values,
                            "schedule": schedule_of(values),
                        },
                        indent=2,
                        ensure_ascii=False,
                    )
                )
            else:
                print_report(info, values, status)

            if args.write_test or args.set:
                status = run_writes(session, schema, status, args, log)
                values = schema.decode(status)

            if args.watch > 0:
                log(f"\nWatching for {args.watch:g} s (change something in the app)...")
                end = time.monotonic() + args.watch
                next_ping = 0.0
                while time.monotonic() < end:
                    if time.monotonic() >= next_ping:
                        session.ping()
                        next_ping = time.monotonic() + 4.0
                    for block in session.poll(1.0, schema.length):
                        new = schema.decode(block)
                        print_changes(values, new)
                        values = new
        finally:
            session.close()
    except (ProbeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
