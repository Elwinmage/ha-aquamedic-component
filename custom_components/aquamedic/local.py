"""Local (LAN) access to Gizwits pumps, without going through the cloud.

The pump answers on the local network with the same datapoints the cloud
reports, under the same names. This module holds the whole exchange and has no
dependency on Home Assistant, so it can be tested against a fake pump.

Protocol, as checked on a SmartDrift 11.1 (module firmware 04020B25):

* UDP 12414: ``0x0003`` asks, ``0x0004`` answers with length-prefixed fields
  (did, mac, firmware, product key).
* TCP 12416: ``0x0006`` asks for a passcode, ``0x0008`` logs in with it, then
  ``0x0093`` carries the status exchanges. A read is action ``0x02`` and is
  answered by ``0x0094`` (action ``0x03``). A write is action ``0x01`` followed
  by one flag bit per datapoint id and the data block: the last status, with
  the changed datapoints replaced. The pump then reports the new status.
* A packet is ``00 00 00 03``, a varint length, ``00``, the command and the
  payload.

Every call opens its own connection and closes it: the pump only accepts a
few clients, and a short exchange per poll avoids keeping a session alive.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import struct
from typing import Any

_LOGGER = logging.getLogger(__name__)

UDP_PORT = 12414
TCP_PORT = 12416

HEADER = b"\x00\x00\x00\x03"
CMD_DISCOVER = 0x0003
CMD_DISCOVER_REPLY = 0x0004
CMD_PASSCODE_REQ = 0x0006
CMD_PASSCODE_RESP = 0x0007
CMD_LOGIN_REQ = 0x0008
CMD_LOGIN_RESP = 0x0009
CMD_P0 = 0x0093
# Status packets: 0x0091 / 0x0093 (pushed by the pump) and 0x0094 (read reply).
P0_COMMANDS = (0x0091, 0x0093, 0x0094)
ACTION_WRITE = 0x01
ACTION_READ = 0x02
ACTION_READ_REPLY = 0x03
ACTION_REPORT = 0x04

# Written together with the key, at its current value: the EcoDrift / SmartDrift
# firmware ignores a write that changes the flow alone.
COMPANIONS = {"Flow": "Frequency"}

# Controls confirmed on a real pump (EcoDrift 8.3 by the aquamedic-local
# project, SmartDrift 11.1 here). Anything else is sent through the cloud.
LOCAL_WRITABLE = frozenset(
    {
        "SwitchON",
        "PulseTide",
        "FeedSwitch",
        "TimerON",
        "Mode",
        "Linkage",
        "Flow",
        "Frequency",
        "FeedTime",
    }
)

DEFAULT_TIMEOUT = 5.0


class LocalError(Exception):
    """The pump could not be reached, or did not do what was asked."""


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


def split_packet(data: bytes) -> tuple[int, bytes, int] | None:
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
            raise LocalError("bad packet length")
    if length < 3 or len(data) < i + length:
        return None
    body = data[i : i + length]
    return struct.unpack(">H", body[1:3])[0], body[3:], i + length


def _lv_fields(payload: bytes) -> list[bytes]:
    out, i = [], 0
    while i + 2 <= len(payload):
        size = struct.unpack(">H", payload[i : i + 2])[0]
        i += 2
        out.append(payload[i : i + size])
        i += size
    return out


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


# ── Datapoint schema ──────────────────────────────────────────────────────────


class LocalSchema:
    """Layout of the status block, from a Gizwits datapoint document."""

    def __init__(self, document: dict[str, Any]) -> None:
        datapoints = document.get("datapoints", document)
        if isinstance(datapoints.get("data"), dict):
            datapoints = datapoints["data"]
        try:
            self.attrs: list[dict[str, Any]] = datapoints["entities"][0]["attrs"]
            self.length = max(self._end(a) for a in self.attrs)
            self.by_name = {a["name"]: a for a in self.attrs}
            writable = [a for a in self.attrs if a.get("type") == "status_writable"]
            self.write_length = max(self._end(a) for a in writable)
            # One flag bit per datapoint id, big-endian, in the smallest whole
            # number of bytes.
            self.flag_bytes = (max(a["id"] for a in writable) + 8) // 8
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LocalError("unusable datapoint document") from exc
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

    def decode(self, status: bytes) -> dict[str, Any]:
        """Every datapoint as the cloud reports it.

        Booleans stay booleans, numbers and enum indexes are integers and
        binary datapoints are hex strings.
        """
        if len(status) < self.length:
            raise LocalError(f"status too short: {len(status)} < {self.length}")
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


# ── Discovery ─────────────────────────────────────────────────────────────────


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, replies: asyncio.Queue[tuple[bytes, str]]) -> None:
        self._replies = replies

    def datagram_received(self, data: bytes, addr: Any) -> None:
        self._replies.put_nowait((data, addr[0]))


async def async_discover(
    host: str, *, timeout: float = 3.0, udp_port: int = UDP_PORT
) -> dict[str, str] | None:
    """Ask the pump at *host* who it is: did, mac, firmware, product key."""
    loop = asyncio.get_running_loop()
    replies: asyncio.Queue[tuple[bytes, str]] = asyncio.Queue()
    try:
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _DiscoveryProtocol(replies), remote_addr=(host, udp_port)
        )
    except OSError as exc:
        _LOGGER.debug("Local discovery of %s failed: %s", host, exc)
        return None
    try:
        deadline = loop.time() + timeout
        next_send = 0.0
        while (remaining := deadline - loop.time()) > 0:
            if loop.time() >= next_send:
                transport.sendto(build_packet(CMD_DISCOVER))
                next_send = loop.time() + 1.0
            try:
                data, _ip = await asyncio.wait_for(replies.get(), min(remaining, 1.0))
            except TimeoutError:
                continue
            parsed = split_packet(data)
            if parsed is None or parsed[0] != CMD_DISCOVER_REPLY:
                continue
            fields = _lv_fields(parsed[1])
            if len(fields) < 4 or len(fields[3]) != 32:
                continue
            return {
                "ip": host,
                "did": fields[0].decode("ascii", "replace"),
                "mac": fields[1].hex(":"),
                "firmware": fields[2].decode("ascii", "replace"),
                "product_key": fields[3].decode("ascii", "replace"),
            }
    finally:
        transport.close()
    return None


# ── Session ───────────────────────────────────────────────────────────────────


class _Session:
    """One logged-in TCP session with a pump."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        timeout: float,
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._timeout = timeout
        self._buf = b""
        self._sn = 0

    @classmethod
    async def open(cls, host: str, port: int, timeout: float) -> _Session:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout
            )
        except (OSError, TimeoutError) as exc:
            raise LocalError(f"cannot connect to {host}: {exc}") from exc
        session = cls(reader, writer, timeout)
        try:
            await session._login()
        except BaseException:
            await session.close()
            raise
        return session

    async def close(self) -> None:
        self._writer.close()
        with contextlib.suppress(OSError, TimeoutError):
            await asyncio.wait_for(self._writer.wait_closed(), 1.0)

    async def _packets(self, timeout: float) -> list[tuple[int, bytes]]:
        """Wait up to *timeout* s for data and return the packets complete so far."""
        try:
            chunk = await asyncio.wait_for(self._reader.read(4096), timeout)
        except TimeoutError:
            return []
        except OSError as exc:
            raise LocalError(f"connection lost: {exc}") from exc
        if not chunk:
            raise LocalError("the pump closed the connection")
        self._buf += chunk
        out: list[tuple[int, bytes]] = []
        while True:
            if self._buf[:4] != HEADER[: min(4, len(self._buf))]:
                idx = self._buf.find(HEADER, 1)
                self._buf = self._buf[idx:] if idx > 0 else b""
                if not self._buf:
                    break
            found = split_packet(self._buf)
            if found is None:
                break
            cmd, payload, used = found
            self._buf = self._buf[used:]
            out.append((cmd, payload))
        return out

    async def _wait_for(self, cmd: int) -> bytes:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timeout
        while (remaining := deadline - loop.time()) > 0:
            for got, payload in await self._packets(min(remaining, 0.5)):
                if got == cmd:
                    return payload
        raise LocalError(f"no answer (command 0x{cmd:04x}) from the pump")

    async def _send(self, packet: bytes) -> None:
        try:
            self._writer.write(packet)
            await asyncio.wait_for(self._writer.drain(), self._timeout)
        except (OSError, TimeoutError) as exc:
            raise LocalError(f"cannot send to the pump: {exc}") from exc

    async def _login(self) -> None:
        await self._send(build_packet(CMD_PASSCODE_REQ))
        payload = await self._wait_for(CMD_PASSCODE_RESP)
        size = struct.unpack(">H", payload[:2])[0] if len(payload) >= 2 else 0
        passcode = payload[2 : 2 + size]
        if not passcode:
            raise LocalError("the pump gave no passcode (not in binding mode)")
        await self._send(
            build_packet(CMD_LOGIN_REQ, struct.pack(">H", len(passcode)) + passcode)
        )
        if (await self._wait_for(CMD_LOGIN_RESP))[:1] != b"\x00":
            raise LocalError("login refused by the pump")

    async def read_status(self, length: int) -> bytes:
        self._sn += 1
        await self._send(
            build_packet(CMD_P0, struct.pack(">I", self._sn) + bytes([ACTION_READ]))
        )
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timeout
        while (remaining := deadline - loop.time()) > 0:
            for cmd, payload in await self._packets(min(remaining, 0.5)):
                status = status_from_packet(cmd, payload, length)
                if status is not None:
                    return status
        raise LocalError(f"no status of {length} bytes received")

    async def write(self, flags: bytes, data: bytes) -> None:
        self._sn += 1
        payload = struct.pack(">I", self._sn) + bytes([ACTION_WRITE]) + flags + data
        await self._send(build_packet(CMD_P0, payload))

    async def wait_for_values(
        self, schema: LocalSchema, expected: dict[str, int]
    ) -> bytes:
        """Wait until the pump reports *expected*, and return that status."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timeout
        while (remaining := deadline - loop.time()) > 0:
            for cmd, payload in await self._packets(min(remaining, 0.5)):
                block = status_from_packet(cmd, payload, schema.length)
                if block is None:
                    continue
                reported = schema.decode(block)
                if all(int(reported[n]) == v for n, v in expected.items()):
                    return block
        shown = ", ".join(f"{n}={v}" for n, v in expected.items())
        raise LocalError(f"the pump did not report {shown} (write not applied?)")


# ── Pump ──────────────────────────────────────────────────────────────────────


class LocalPump:
    """Reads and writes one pump on the local network."""

    def __init__(
        self,
        host: str,
        schema: LocalSchema,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        tcp_port: int = TCP_PORT,
    ) -> None:
        self.host = host
        self.schema = schema
        self._timeout = timeout
        self._port = tcp_port
        # One exchange at a time: the pump only accepts a few clients.
        self._lock = asyncio.Lock()

    @staticmethod
    def can_write(attrs: dict[str, Any]) -> bool:
        """True when every datapoint of *attrs* may be written locally."""
        return bool(attrs) and set(attrs) <= LOCAL_WRITABLE

    async def async_read(self) -> dict[str, Any]:
        """The current value of every datapoint."""
        async with self._lock:
            session = await _Session.open(self.host, self._port, self._timeout)
            try:
                status = await session.read_status(self.schema.length)
            finally:
                await session.close()
        return self.schema.decode(status)

    async def async_write(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Write *attrs* and return the datapoints the pump reports afterwards."""
        if not self.can_write(attrs):
            raise LocalError(f"not writable locally: {', '.join(sorted(attrs))}")
        changes = {name: int(value) for name, value in attrs.items()}
        async with self._lock:
            session = await _Session.open(self.host, self._port, self._timeout)
            try:
                status = await session.read_status(self.schema.length)
                current = self.schema.decode(status)
                for name, companion in COMPANIONS.items():
                    if name in changes and companion not in changes:
                        changes[companion] = int(current[companion])
                flags, data = self.schema.encode_write(status, changes)
                await session.write(flags, data)
                status = await session.wait_for_values(self.schema, changes)
            finally:
                await session.close()
        return self.schema.decode(status)
