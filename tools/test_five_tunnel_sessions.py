"""Independent lifecycle model and source invariants for five UDP tunnels."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src" / "main.cpp").read_text(encoding="utf-8")
E_NO_MORE_CONNECTIONS = 0x24
ADDRESSES = [0x2121, 0x2122, 0x2123, 0x2124, 0x2125]


class Slot:
    def __init__(self, address):
        self.address = address
        self.channel = None
        self.rx = 0
        self.pending_ack = None
        self.queue = []
        self.last_activity = 0


class Server:
    def __init__(self):
        self.slots = [Slot(a) for a in ADDRESSES]
        self.management_channel = None
        self.next_channel = 0

    def channel(self):
        used = {s.channel for s in self.slots if s.channel is not None}
        used.add(self.management_channel)
        while True:
            self.next_channel = (self.next_channel + 1) & 0xFF
            if self.next_channel and self.next_channel not in used:
                return self.next_channel

    def connect(self):
        for slot in self.slots:
            if slot.address and slot.channel is None:
                slot.channel = self.channel()
                return 0, slot
        return E_NO_MORE_CONNECTIONS, None

    @staticmethod
    def request(slot, sequence, payload):
        if sequence == ((slot.rx - 1) & 0xFF):
            return "duplicate-ack", False
        if sequence != slot.rx:
            return "sequence-error", False
        slot.rx = (slot.rx + 1) & 0xFF
        slot.queue.append(payload)
        return "ack", True

    @staticmethod
    def disconnect(slot):
        slot.channel = None
        slot.queue.clear()
        slot.pending_ack = None

    def expire(self, now, timeout):
        expired = []
        for slot in self.slots:
            if slot.channel is not None and now - slot.last_activity >= timeout:
                expired.append(slot)
                self.disconnect(slot)
        return expired


server = Server()
connected = [server.connect() for _ in range(5)]
assert all(status == 0 for status, _ in connected)
channels = [slot.channel for _, slot in connected]
assert len(set(channels)) == 5
server.management_channel = server.channel()
assert server.management_channel not in channels
assert server.connect() == (E_NO_MORE_CONNECTIONS, None)

first = connected[0][1]
assert server.request(first, 0, b"one") == ("ack", True)
assert server.request(first, 0, b"one") == ("duplicate-ack", False)
assert len(first.queue) == 1
first.pending_ack = 7
assert first.pending_ack == 7
assert all(slot.pending_ack is None for _, slot in connected[1:])
second = connected[1][1]
assert server.request(second, 0, b"two") == ("ack", True)
server.disconnect(first)
assert second.channel == channels[1] and second.queue == [b"two"]
status, reused = server.connect()
assert status == 0 and reused is first
assert reused.channel not in {second.channel, server.management_channel}
reused.last_activity = 1
for _, slot in connected[1:]:
    slot.last_activity = 100
assert server.expire(121, 120) == [reused]
assert reused.channel is None and second.channel is not None

assert "tunnels[kTunnelSlots]" in SOURCE
assert "TunnelTpRequest tpRequests[kTunnelTpQueueDepth]" in SOURCE
assert "slot.tpRequestCount<kTunnelTpQueueDepth" in SOURCE
assert "sequence==uint8_t(slot->rxSequence-1)" in SOURCE
assert "else if(type==4&&!freeSlot)status=0x24" in SOURCE
assert "event.ownerIndex<kTunnelSlots" in SOURCE
assert "cemi.destinationAddress()==slot.address" in SOURCE
assert "tunnelArbiterNext=(index+1)%kTunnelSlots" in SOURCE
assert "validTunnelAddresses" in SOURCE

print("OK: five tunnels, sixth refused, isolated sequences/ACKs, duplicate suppression, disconnect and slot reuse")
