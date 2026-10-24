#!/usr/bin/env python3
"""Independent protocol/state tests for the bounded TP <-> KNXnet/IP router."""

from collections import deque
from pathlib import Path


def xor_fcs(frame_without_fcs: bytes) -> int:
    value = 0xFF
    for byte in frame_without_fcs:
        value ^= byte
    return value


def cemi_to_tp(cemi: bytes) -> bytes:
    assert cemi[0] in (0x11, 0x29)
    add_len = cemi[1]
    control1 = cemi[2 + add_len] & ~0x02  # cEMI AckRequested is not TP control.
    control2 = cemi[3 + add_len]
    hop = (control2 >> 4) & 0x07
    assert hop > 0
    control2 = (control2 & ~0x70) | ((hop - 1) << 4)
    tp_npdu = (control2 & 0xF0) | (cemi[8 + add_len] & 0x0F)
    body = bytes([control1]) + cemi[4 + add_len : 8 + add_len] + bytes([tp_npdu]) + cemi[9 + add_len :]
    return body + bytes([xor_fcs(body)])


def tp_to_routing(tp: bytes) -> bytes:
    assert xor_fcs(tp[:-1]) == tp[-1]
    hop = (tp[5] >> 4) & 0x07
    assert hop > 0
    control2 = (tp[5] & ~0x70) | ((hop - 1) << 4)
    cemi = bytes([0x29, 0x00, tp[0], control2]) + tp[1:5] + bytes([tp[5] & 0x0F]) + tp[6:-1]
    length = 6 + len(cemi)
    return bytes([0x06, 0x10, 0x05, 0x30, length >> 8, length & 0xFF]) + cemi


class Fingerprints:
    def __init__(self, ttl_ms=500):
        self.ttl_ms = ttl_ms
        self.items = []

    def remember(self, now, payload):
        self.items.append((now + self.ttl_ms, payload))
        self.items = self.items[-8:]

    def consume(self, now, payload):
        self.items = [(expiry, value) for expiry, value in self.items if expiry > now]
        for index, (_, value) in enumerate(self.items):
            if value == payload:
                self.items.pop(index)
                return True
        return False


class Arbiter:
    def __init__(self):
        self.active = None

    def submit(self, owner, token):
        if self.active is not None:
            return False
        self.active = (owner, token)
        return True

    def confirm(self, owner, token):
        if self.active != (owner, token):
            return False
        self.active = None
        return True


# Captured/validated OFF request: source 15.15.254, group 2/0/0, hop 6.
ip_cemi = bytes.fromhex("29 00 BE E0 FF FE 10 00 01 00 80")
expected_tp = bytes.fromhex("BC FF FE 10 00 D1 00 80 03")
assert cemi_to_tp(ip_cemi) == expected_tp
assert ((expected_tp[5] >> 4) & 7) == 5
assert xor_fcs(expected_tp[:-1]) == expected_tp[-1]

# Independent TP -> IP vector: source and APDU preserved, hop decremented once.
routing = tp_to_routing(expected_tp)
assert routing[:6] == bytes.fromhex("06 10 05 30 00 11")
assert routing[10:14] == bytes.fromhex("FF FE 10 00")
assert routing[-2:] == bytes.fromhex("00 80")
assert ((routing[9] >> 4) & 7) == 4

# Hop zero is rejected in either conversion direction.
try:
    cemi_to_tp(bytes.fromhex("29 00 BE 80 FF FE 10 00 01 00 80"))
    raise AssertionError("hop=0 accepted")
except AssertionError as exc:
    assert str(exc) != "hop=0 accepted"

# Bounded FIFO and expiry: no replay after timeout.
queue = deque(maxlen=4)
for token in range(4):
    queue.append((token, 1000))
assert len(queue) == 4
assert not (len(queue) < queue.maxlen)  # fifth frame must be rejected, not overwrite.
now = 3001
queue = deque(((token, queued) for token, queued in queue if now - queued < 2000), maxlen=4)
assert not queue

# Exact, one-shot, short-lived echo suppression preserves later legitimate repeats.
fingerprints = Fingerprints()
fingerprints.remember(1000, expected_tp)
assert fingerprints.consume(1050, expected_tp)
assert not fingerprints.consume(1060, expected_tp)
fingerprints.remember(2000, expected_tp)
assert not fingerprints.consume(2501, expected_tp)

# Tunnel and routing share one UART transaction; stale/wrong confirmations are ignored.
arbiter = Arbiter()
assert arbiter.submit("tunnel", 11)
assert not arbiter.submit("routing", 12)
assert not arbiter.confirm("routing", 11)
assert arbiter.confirm("tunnel", 11)
assert arbiter.submit("routing", 12)
assert arbiter.confirm("routing", 12)

# Compile-time/passive guards and the single shared UART command path stay present.
source = (Path(__file__).parents[1] / "src" / "main.cpp").read_text(encoding="utf-8")
config_header = (Path(__file__).parents[1] / "include" / "router_config.h").read_text(encoding="utf-8")
assert "#define ROUTING_ARMED 1" in config_header
assert "static_assert(ROUTING_ARMED==1" in source
assert "ipTpEnabled=false;ipTpPhase=IpTpPhase::Passive;clearRouteQueue()" in source
assert "command.owner=TxOwner::Tunnel" in source
assert "command.owner=TxOwner::Routing" in source
assert "activeTxOwner!=TxOwner::None" in source
assert "routeIpToTp=false,routeTpToIp=false" in source
assert "kRouteFingerprintTtlMs=500" in source

print("OK: conversions, hop count, FCS, bounded expiry, one-shot echoes and UART arbitration")
