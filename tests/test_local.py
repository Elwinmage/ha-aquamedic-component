"""Tests for local.py, against a fake pump on the loopback interface."""

from __future__ import annotations

import asyncio
import json
import pathlib
import struct
from typing import Any

import pytest

from custom_components.aquamedic import local
from custom_components.aquamedic.const import (
    REEFDOSER_EVO5_PRODUCT_KEY,
    SMARTDRIFT_PRODUCT_KEY,
)
from custom_components.aquamedic.local import (
    LocalError,
    LocalPump,
    LocalSchema,
    async_discover,
    build_packet,
    split_packet,
    status_from_packet,
)

CAPTURE = next(
    pathlib.Path(__file__).parent.parent.glob(
        f"scripts/devices_datapoints/*_{SMARTDRIFT_PRODUCT_KEY}.json"
    )
)
DID = "didMOCK123"
TIMEOUT = 0.6


@pytest.fixture(scope="module")
def schema() -> LocalSchema:
    return LocalSchema(json.loads(CAPTURE.read_text(encoding="utf-8")))


def _lv(data: bytes) -> bytes:
    return struct.pack(">H", len(data)) + data


# No real socket is opened (the Home Assistant test plugin forbids it): the
# pump lives in memory behind the stream objects the client talks to.


class FakeReader:
    """What the pump sends: chunks read one by one, b"" meaning the pump hung up."""

    def __init__(self) -> None:
        self._chunks: asyncio.Queue[bytes] = asyncio.Queue()

    def put(self, chunk: bytes) -> None:
        self._chunks.put_nowait(chunk)

    async def read(self, _size: int) -> bytes:
        return await self._chunks.get()


class FakeWriter:
    """What the client sends: handed straight to the fake pump."""

    def __init__(self, pump: FakePump, reader: FakeReader) -> None:
        self._pump = pump
        self._reader = reader
        self._buf = b""

    def write(self, data: bytes) -> None:
        self._buf += data
        while (found := split_packet(self._buf)) is not None:
            cmd, payload, used = found
            self._buf = self._buf[used:]
            self._pump.answer(self._reader, cmd, payload)

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        return None

    async def wait_closed(self) -> None:
        return None


class FakePump:
    """A pump speaking the local protocol, with switches to make it misbehave."""

    def __init__(self, schema: LocalSchema) -> None:
        self.schema = schema
        self.status = bytes(schema.length)
        self.passcode = b"PASSCODE12"
        self.login_ok = True
        self.answer_reads = True
        self.apply_writes = True
        self.garbage_first = False
        self.chatty_writes = False
        self.hang_up_after_login = False
        self.refuse_connections = False
        self.writes: list[tuple[bytes, bytes]] = []

    def set(self, **values: int) -> None:
        _flags, data = self.schema.encode_write(self.status, values)
        self.status = data + self.status[len(data) :]

    async def open_connection(
        self, _host: str, _port: int
    ) -> tuple[FakeReader, FakeWriter]:
        if self.refuse_connections:
            raise ConnectionRefusedError("refused")
        reader = FakeReader()
        return reader, FakeWriter(self, reader)

    def answer(self, reader: FakeReader, cmd: int, payload: bytes) -> None:
        """Reply to one packet."""
        if cmd == local.CMD_PASSCODE_REQ:
            if self.garbage_first:
                reader.put(b"\xff\xff\xff")  # too short to hold a header
                reader.put(b"\x01\x02\x03\x04\x05")  # no header at all
                reader.put(b"\xff\xff" + build_packet(0x0016))  # junk, then a pong
            reader.put(
                build_packet(local.CMD_PASSCODE_RESP, _lv(self.passcode))
                if self.passcode
                else build_packet(local.CMD_PASSCODE_RESP)
            )
        elif cmd == local.CMD_LOGIN_REQ:
            reader.put(
                build_packet(
                    local.CMD_LOGIN_RESP, b"\x00" if self.login_ok else b"\x01"
                )
            )
            if self.hang_up_after_login:
                reader.put(b"")
        elif cmd == local.CMD_P0:
            sn, action = payload[:4], payload[4]
            if action == local.ACTION_READ and self.answer_reads:
                reader.put(
                    build_packet(
                        0x0094, sn + bytes([local.ACTION_READ_REPLY]) + self.status
                    )
                )
            elif action == local.ACTION_WRITE:
                size = self.schema.flag_bytes
                flags = payload[5 : 5 + size]
                data = payload[5 + size :]
                self.writes.append((flags, data))
                if self.apply_writes:
                    self.status = data + self.status[len(data) :]
                if self.chatty_writes:
                    reader.put(build_packet(0x0016))  # a pong, not a status
                reader.put(
                    build_packet(
                        0x0094, sn + bytes([local.ACTION_REPORT]) + self.status
                    )
                )


@pytest.fixture
def pump(schema, monkeypatch):
    fake = FakePump(schema)
    monkeypatch.setattr(asyncio, "open_connection", fake.open_connection)
    return fake


def _client(
    _fake: FakePump, schema: LocalSchema, timeout: float = TIMEOUT
) -> LocalPump:
    return LocalPump("127.0.0.1", schema, timeout=timeout)


# ── Framing ───────────────────────────────────────────────────────────────────


def test_packet_round_trip_with_a_long_payload():
    payload = bytes(range(256)) * 2
    cmd, got, used = split_packet(build_packet(0x0093, payload))
    assert (cmd, got) == (0x0093, payload)
    assert used == len(build_packet(0x0093, payload))


def test_split_packet_waits_for_a_complete_packet():
    packet = build_packet(0x0093, b"abcdef")
    assert split_packet(packet[:3]) is None
    assert split_packet(packet[:-1]) is None
    # The length itself is cut short.
    assert split_packet(local.HEADER + b"\x80") is None


def test_split_packet_refuses_a_foreign_header():
    assert split_packet(b"\x01\x02\x03\x04\x05\x06") is None


def test_split_packet_refuses_a_runaway_length():
    with pytest.raises(LocalError, match="bad packet length"):
        split_packet(local.HEADER + b"\xff\xff\xff\xff\xff\x01")


def test_split_packet_ignores_a_body_too_short_to_hold_a_command():
    assert split_packet(local.HEADER + b"\x02\x00\x00") is None


def test_status_from_packet():
    status = bytes(range(10))
    assert status_from_packet(0x0094, b"\x00\x00\x00\x01\x03" + status, 10) == status
    assert status_from_packet(0x0093, b"\x00\x00\x00\x01\x04" + status, 10) == status
    # Neither a read reply nor a report: an echo of a command.
    assert status_from_packet(0x0094, b"\x00\x00\x00\x01\x01" + status, 10) is None
    # Not a status command, or too short.
    assert status_from_packet(0x0007, b"\x00\x00\x00\x01\x03" + status, 10) is None
    assert status_from_packet(0x0094, b"\x03" + status[:5], 10) is None


# ── Schema ────────────────────────────────────────────────────────────────────


def test_schema_layout(schema):
    assert schema.length == 393
    assert schema.write_length == 392
    assert schema.flag_bytes == 8


def test_schema_accepts_the_cloud_wrappers():
    document = json.loads(CAPTURE.read_text(encoding="utf-8"))["datapoints"]
    assert LocalSchema(document).length == 393
    assert LocalSchema({"data": document}).length == 393


@pytest.mark.parametrize("document", [{}, {"entities": []}, {"entities": [{}]}])
def test_schema_refuses_an_unusable_document(document):
    with pytest.raises(LocalError, match="unusable"):
        LocalSchema(document)


def test_decode_follows_the_datapoint_types(schema):
    _flags, data = schema.encode_write(
        bytes(schema.length),
        {"SwitchON": 1, "TimerON": 1, "Mode": 3, "Flow": 61, "Frequency": 100},
    )
    status = bytearray(data + bytes(schema.length - len(data)))
    offset = schema.by_name["AutoTime00"]["position"]["byte_offset"]
    status[offset] = 0xAB  # first byte of the first timer slot
    values = schema.decode(bytes(status))
    assert values["SwitchON"] is True
    assert values["PulseTide"] is False
    assert values["TimerON"] is True
    assert values["Mode"] == 3
    assert values["Flow"] == 61
    assert values["Frequency"] == 100
    assert isinstance(values["AutoTime00"], str)
    assert values["AutoTime00"].startswith("ab")


def test_decode_refuses_a_short_status(schema):
    with pytest.raises(LocalError, match="too short"):
        schema.decode(bytes(10))


def test_encode_write_changes_only_what_is_asked(schema):
    _flags, data = schema.encode_write(
        bytes(schema.length), {"SwitchON": 1, "TimerON": 1, "Frequency": 77}
    )
    base = data + bytes(schema.length - len(data))
    flags, data = schema.encode_write(base, {"Flow": 55, "Mode": 3, "SwitchON": 0})
    assert int.from_bytes(flags, "big") == (1 << 8) | (1 << 5) | (1 << 0)
    assert len(flags) == 8
    assert len(data) == 392
    values = schema.decode(data + bytes(schema.length - len(data)))
    assert values["Flow"] == 55
    assert values["Mode"] == 3
    assert values["SwitchON"] is False
    # What was not asked for keeps its value.
    assert values["TimerON"] is True
    assert values["Frequency"] == 77


# ── Discovery ─────────────────────────────────────────────────────────────────


class FakeDatagramTransport:
    """A UDP socket whose peer answers every datagram with the given replies."""

    def __init__(
        self, protocol: asyncio.DatagramProtocol, replies: list[bytes], host: str
    ) -> None:
        self._protocol = protocol
        self._replies = replies
        self._host = host
        self.closed = False

    def sendto(self, _data: bytes) -> None:
        loop = asyncio.get_running_loop()
        for reply in self._replies:
            loop.call_soon(self._protocol.datagram_received, reply, (self._host, 1))

    def close(self) -> None:
        self.closed = True


def _fake_udp(monkeypatch, replies: list[bytes]) -> list[FakeDatagramTransport]:
    made: list[FakeDatagramTransport] = []

    async def create(factory, remote_addr=None, **_kwargs):
        protocol = factory()
        transport = FakeDatagramTransport(protocol, replies, remote_addr[0])
        made.append(transport)
        return transport, protocol

    monkeypatch.setattr(asyncio.get_running_loop(), "create_datagram_endpoint", create)
    return made


def _discovery_reply(product_key: bytes = SMARTDRIFT_PRODUCT_KEY.encode()) -> bytes:
    fields = (
        _lv(DID.encode())
        + _lv(bytes.fromhex("aabbccddeeff"))
        + _lv(b"04020B25")
        + _lv(product_key)
    )
    return build_packet(local.CMD_DISCOVER_REPLY, fields)


async def test_discover_identifies_the_pump(monkeypatch):
    made = _fake_udp(
        monkeypatch,
        [
            b"garbage",  # not a packet
            build_packet(0x0007),  # not the answer to a discovery
            build_packet(local.CMD_DISCOVER_REPLY, _lv(b"too") + _lv(b"few")),
            _discovery_reply(b"short-key"),  # product key of the wrong size
            _discovery_reply(),
        ],
    )
    info = await async_discover("10.0.0.5", timeout=2.0)
    assert info == {
        "ip": "10.0.0.5",
        "did": DID,
        "mac": "aa:bb:cc:dd:ee:ff",
        "firmware": "04020B25",
        "product_key": SMARTDRIFT_PRODUCT_KEY,
    }
    assert made[0].closed


async def test_discover_gives_up_when_nobody_answers(monkeypatch):
    made = _fake_udp(monkeypatch, [])
    assert await async_discover("10.0.0.5", timeout=0.3) is None
    assert made[0].closed


async def test_discover_gives_up_on_an_unusable_address(monkeypatch):
    async def refuse(*_args, **_kwargs):
        raise OSError("name resolution failed")

    monkeypatch.setattr(asyncio.get_running_loop(), "create_datagram_endpoint", refuse)
    assert await async_discover("not a host name", timeout=0.3) is None


# ── Reads ─────────────────────────────────────────────────────────────────────


async def test_read_returns_every_datapoint(pump, schema):
    pump.set(Flow=61, Frequency=95, SwitchON=1, TimerON=1, Mode=3)
    values = await _client(pump, schema).async_read()
    assert values["Flow"] == 61
    assert values["Frequency"] == 95
    assert values["SwitchON"] is True
    assert values["Mode"] == 3


async def test_read_survives_garbage_on_the_wire(pump, schema):
    pump.garbage_first = True
    assert (await _client(pump, schema).async_read())["Flow"] == 0


async def test_read_fails_when_the_pump_is_unreachable(pump, schema):
    pump.refuse_connections = True
    with pytest.raises(LocalError, match="cannot connect"):
        await _client(pump, schema).async_read()


async def test_read_fails_when_the_connection_times_out(schema, monkeypatch):
    async def never(*_args: Any, **_kwargs: Any):
        await asyncio.sleep(5)

    monkeypatch.setattr(asyncio, "open_connection", never)
    with pytest.raises(LocalError, match="cannot connect"):
        await LocalPump("10.0.0.1", schema, timeout=0.1).async_read()


async def test_login_needs_a_passcode(pump, schema):
    pump.passcode = b""
    with pytest.raises(LocalError, match="no passcode"):
        await _client(pump, schema).async_read()


async def test_login_can_be_refused(pump, schema):
    pump.login_ok = False
    with pytest.raises(LocalError, match="login refused"):
        await _client(pump, schema).async_read()


async def test_login_gets_no_answer(pump, schema, monkeypatch):
    monkeypatch.setattr(FakePump, "answer", lambda *_args: None)
    with pytest.raises(LocalError, match="no answer"):
        await _client(pump, schema, timeout=0.3).async_read()


async def test_read_gets_no_status(pump, schema):
    pump.answer_reads = False
    with pytest.raises(LocalError, match="no status"):
        await _client(pump, schema, timeout=0.3).async_read()


async def test_read_fails_when_the_pump_hangs_up(pump, schema):
    pump.hang_up_after_login = True
    with pytest.raises(LocalError, match="closed the connection"):
        await _client(pump, schema).async_read()


async def test_a_dropped_connection_while_sending_is_reported(schema):
    class BrokenWriter:
        def write(self, _data: bytes) -> None:
            raise ConnectionResetError("reset")

    session = local._Session(None, BrokenWriter(), 0.2)  # type: ignore[arg-type]
    with pytest.raises(LocalError, match="cannot send"):
        await session._send(b"x")


async def test_a_reset_while_receiving_is_reported(schema):
    class ResettingReader:
        async def read(self, _size: int) -> bytes:
            raise ConnectionResetError("reset")

    session = local._Session(ResettingReader(), None, 0.2)  # type: ignore[arg-type]
    with pytest.raises(LocalError, match="connection lost"):
        await session._packets(0.2)


# ── Writes ────────────────────────────────────────────────────────────────────


def test_can_write_only_the_confirmed_controls():
    assert LocalPump.can_write({"Flow": 40, "Frequency": 30})
    assert LocalPump.can_write({"TimerON": True})
    assert not LocalPump.can_write({})
    assert not LocalPump.can_write({"Flow": 40, "AutoTime00": "00"})


async def test_write_changes_the_pump_and_returns_what_it_reports(pump, schema):
    pump.set(Flow=30, Frequency=30, FeedTime=10)
    values = await _client(pump, schema).async_write({"FeedTime": 11})
    assert values["FeedTime"] == 11
    assert values["Flow"] == 30
    assert len(pump.writes) == 1
    flags, data = pump.writes[0]
    assert int.from_bytes(flags, "big") == 1 << schema.by_name["FeedTime"]["id"]
    assert len(data) == schema.write_length


async def test_a_flow_write_carries_the_current_frequency(pump, schema):
    pump.set(Flow=30, Frequency=60)
    values = await _client(pump, schema).async_write({"Flow": 35})
    assert (values["Flow"], values["Frequency"]) == (35, 60)
    flags, _data = pump.writes[0]
    expected = (1 << schema.by_name["Flow"]["id"]) | (
        1 << schema.by_name["Frequency"]["id"]
    )
    assert int.from_bytes(flags, "big") == expected


async def test_a_write_keeps_an_explicit_frequency(pump, schema):
    pump.set(Flow=30, Frequency=60)
    values = await _client(pump, schema).async_write({"Flow": 35, "Frequency": 80})
    assert (values["Flow"], values["Frequency"]) == (35, 80)


async def test_booleans_are_written_as_numbers(pump, schema):
    pump.set(TimerON=1)
    values = await _client(pump, schema).async_write({"TimerON": False})
    assert values["TimerON"] is False


async def test_a_write_waits_through_packets_that_are_not_a_status(pump, schema):
    pump.chatty_writes = True
    values = await _client(pump, schema).async_write({"FeedTime": 13})
    assert values["FeedTime"] == 13


async def test_a_write_the_pump_does_not_apply_is_an_error(pump, schema):
    pump.apply_writes = False
    with pytest.raises(LocalError, match="did not report"):
        await _client(pump, schema, timeout=0.4).async_write({"FeedTime": 12})


async def test_an_unsupported_write_is_refused_before_connecting(pump, schema):
    pump.refuse_connections = True  # never reached
    with pytest.raises(LocalError, match="not writable locally"):
        await _client(pump, schema).async_write({"AutoTime00": "00"})


# ── Reefdoser EVO 5 (layout of the datapoint document supplied by a user) ─────

DOSER_CAPTURE = next(
    pathlib.Path(__file__).parent.parent.glob(
        f"scripts/devices_datapoints/*_{REEFDOSER_EVO5_PRODUCT_KEY}.json"
    )
)


@pytest.fixture(scope="module")
def doser_schema() -> LocalSchema:
    return LocalSchema(json.loads(DOSER_CAPTURE.read_text(encoding="utf-8")))


def test_doser_schema_layout(doser_schema):
    assert doser_schema.length == 499
    # Everything up to the date and time datapoints is writable.
    assert doser_schema.write_length == 496
    assert doser_schema.flag_bytes == 4


def test_doser_bit_fields_share_one_word(doser_schema):
    """CALSet sits on bits 12-14 of the word made by the first two bytes."""
    flags, data = doser_schema.encode_write(
        bytes(doser_schema.length), {"switch": 1, "CALSet": 4, "Timer5ON": 1}
    )
    assert int.from_bytes(flags, "big") == (1 << 0) | (1 << 12) | (1 << 10)
    assert data[:2] == ((4 << 12) | (1 << 10) | 1).to_bytes(2, "big")
    values = doser_schema.decode(data + bytes(doser_schema.length - len(data)))
    assert values["switch"] is True
    assert values["Timer5ON"] is True
    assert values["CALSet"] == 4
    assert values["channe1"] is False


def test_doser_decodes_the_tail(doser_schema):
    status = bytearray(doser_schema.length)
    status[496] = 120  # time1, seconds
    status[497] = 1  # OpenCircuit
    values = doser_schema.decode(bytes(status))
    assert values["time1"] == 120
    assert values["OpenCircuit"] is True
    assert values["Fault_UART"] is False
    assert len(values["CH5SWTime"]) == 192
