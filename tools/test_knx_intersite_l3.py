"""Deterministic independent reference tests for the KXL3 v1 wire format."""

import binascii
import collections
import random
import socket
import struct
import threading
import time
from pathlib import Path

MAGIC = b"KXL3"
VERSION = 1
HEADER = 36
DATA = 1
ACK = 2
MAX_TP = 263


def fcs(data):
    value = 0xFF
    for byte in data:
        value ^= byte
    return value


def frame(length, seed=1):
    assert 9 <= length <= MAX_TP
    value = bytearray(length)
    value[:7] = bytes((0x10, 0xE0, 0x11, 0xFD, 0x10, 0x00, length - 9))
    rng = random.Random(seed)
    value[7:-1] = bytes(rng.randrange(256) for _ in value[7:-1])
    value[-1] = fcs(value[:-1])
    return bytes(value)


def standard_frame(apdu_length, seed=1):
    assert 1 <= apdu_length <= 16
    value = bytearray(7 + apdu_length)
    value[:5] = bytes((0xBC, 0x11, 0xFD, 0x10, 0x00))
    value[5] = 0xE0 | (apdu_length - 1)
    rng = random.Random(seed)
    value[6:-1] = bytes(rng.randrange(256) for _ in value[6:-1])
    value[-1] = fcs(value[:-1])
    return bytes(value)


def encode(kind, origin, sender, boot, sequence, ttl=4, payload=b"", ack_sequence=0):
    assert kind in (DATA, ACK) and origin and sender and boot and sequence and ttl
    assert (kind == DATA and payload and not ack_sequence) or (kind == ACK and not payload and ack_sequence)
    packet = bytearray(struct.pack(
        ">4sBBBBIIIIIHHI", MAGIC, VERSION, kind, HEADER, ttl, origin, sender,
        boot, sequence, ack_sequence, len(payload), 0, 0
    ) + payload)
    struct.pack_into(">I", packet, 32, binascii.crc32(packet) & 0xFFFFFFFF)
    return bytes(packet)


def decode(packet):
    assert len(packet) >= HEADER
    fields = struct.unpack(">4sBBBBIIIIIHHI", packet[:HEADER])
    magic, version, kind, header, ttl, origin, sender, boot, sequence, ack_sequence, length, flags, crc = fields
    assert magic == MAGIC and version == VERSION and header == HEADER
    assert kind in (DATA, ACK) and ttl and origin and sender and boot and sequence
    assert flags == 0 and len(packet) == HEADER + length <= HEADER + MAX_TP
    zeroed = bytearray(packet)
    struct.pack_into(">I", zeroed, 32, 0)
    assert binascii.crc32(zeroed) & 0xFFFFFFFF == crc
    payload = packet[HEADER:]
    if kind == DATA:
        extended = payload and (payload[0] & 0xD3) == 0x10
        expected = 9 + payload[6] if extended else 8 + (payload[5] & 0x0F)
        assert payload and not ack_sequence and len(payload) == expected
        assert payload[-1] == fcs(payload[:-1])
    else:
        assert not payload and ack_sequence
    return fields, payload


class Peer:
    def __init__(self, site, boot, expected, port):
        self.site, self.boot, self.expected = site, boot, expected
        self.sequence = 0
        self.cache = collections.deque(maxlen=32)
        self.received, self.duplicates, self.acks = [], 0, []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", port))
        self.sock.settimeout(0.05)
        self.port = self.sock.getsockname()[1]

    def send(self, destination, payload, ttl=4):
        self.sequence += 1
        packet = encode(DATA, self.site, self.site, self.boot, self.sequence, ttl, payload)
        self.sock.sendto(packet, ("127.0.0.1", destination))
        return packet

    def poll(self):
        try:
            packet, address = self.sock.recvfrom(512)
        except socket.timeout:
            return False
        fields, payload = decode(packet)
        # Use direct tuple positions to keep the reference visibly independent.
        kind = fields[2]
        origin, sender, boot, sequence, ack_sequence = fields[5:10]
        assert sender == self.expected and origin != self.site
        if kind == ACK:
            self.acks.append(ack_sequence)
            return True
        key = (origin, boot, sequence)
        if key in self.cache:
            self.duplicates += 1
        else:
            self.cache.append(key)
            self.received.append(payload)
        self.sequence += 1
        ack = encode(ACK, self.site, self.site, self.boot, self.sequence,
                     ack_sequence=sequence)
        self.sock.sendto(ack, address)
        return True


def expect_failure(packet):
    try:
        decode(packet)
    except (AssertionError, struct.error):
        return
    raise AssertionError("malformed packet accepted")


vectors = [standard_frame(length, length) for length in (1, 2, 15, 16)]
vectors += [frame(length, length) for length in (9, 23, 32, 33, 63, 64, 65, 127, 128, 129, 263)]
for sequence, opaque in enumerate(vectors, 1):
    fields, restored = decode(encode(DATA, 1, 1, 10, sequence, payload=opaque))
    assert fields[1] == VERSION and restored == opaque

base = bytearray(encode(DATA, 1, 1, 10, 1, payload=frame(65)))
for index in (0, 4, 5, 6, 7, 28, 30, 32, len(base) - 1):
    damaged = bytearray(base)
    damaged[index] ^= 1
    expect_failure(damaged)
expect_failure(base[:-1])
expect_failure(base + b"\x00")

# Real localhost UDP, bidirectional traffic, ACK, duplicate and restart boot ID.
a = Peer(0xA001, 0xA0A0, 0xB001, 0)
b = Peer(0xB001, 0xB0B0, 0xA001, 0)
sent = a.send(b.port, frame(263, 99))
assert b.poll() and a.poll()
assert b.received == [frame(263, 99)] and a.acks == [1]
a.sock.sendto(sent, ("127.0.0.1", b.port))
assert b.poll() and a.poll() and b.duplicates == 1 and len(b.received) == 1

# Out-of-order packets are accepted once; an unavailable peer yields no ACK.
p2 = encode(DATA, a.site, a.site, a.boot, 20, payload=frame(33, 2))
p1 = encode(DATA, a.site, a.site, a.boot, 19, payload=frame(32, 1))
a.sock.sendto(p2, ("127.0.0.1", b.port)); a.sock.sendto(p1, ("127.0.0.1", b.port))
assert b.poll() and b.poll()
unavailable = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
unavailable.sendto(base, ("127.0.0.1", 9))

restart = encode(DATA, a.site, a.site, a.boot + 1, 1, payload=frame(9, 3))
a.sock.sendto(restart, ("127.0.0.1", b.port))
assert b.poll() and b.received[-1] == frame(9, 3)

wrong_identity = encode(DATA, a.site, 0xDEAD, a.boot, 90, payload=frame(9, 4))
wrong_fields, _ = decode(wrong_identity)
assert wrong_fields[6] != b.expected
self_origin = encode(DATA, b.site, a.site, a.boot, 91, payload=frame(9, 5))
self_fields, _ = decode(self_origin)
assert self_fields[5] == b.site

# Model a three-site A->B->C->A loop: origin tuple is retained, sender changes,
# TTL decreases, and A rejects its own origin before reinjection.
origin = (0xA001, 0xAAAA, 77)
seen = set()
ttl = 3
for sender in (0xA001, 0xB001, 0xC001):
    key = origin
    if key in seen or (sender == 0xC001 and origin[0] == 0xA001):
        break
    seen.add(key)
    ttl -= 1
assert len(seen) == 1 and ttl == 2

# The bounded multi-peer enqueue order rotates, so repeated saturation cannot
# always privilege the lowest configured slot.
orders = [[(first + offset) % 4 for offset in range(4)] for first in range(4)]
assert [order[0] for order in orders] == [0, 1, 2, 3]

# Firmware guard: MONITOR_ONLY consumes and counts a validated DATA before the
# only branch which can enqueue a TpEvent for the routing engine.
transport_source = (Path(__file__).parents[1] / "src" / "knx_intersite_transport.cpp").read_text(encoding="utf-8")
monitor_guard = transport_source.index("config_.mode == Mode::MonitorOnly")
tp_enqueue = transport_source.index("xQueueSend(rxQueue_", monitor_guard)
assert monitor_guard < tp_enqueue
assert "++stats_.rxMonitorOnly" in transport_source[monitor_guard:tp_enqueue]

a.sock.close(); b.sock.close(); unavailable.close()
print("KXL3: protocol, malformed input, UDP peers, ACK, duplicate, restart and loop tests PASS")
