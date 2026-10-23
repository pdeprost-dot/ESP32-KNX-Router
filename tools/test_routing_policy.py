#!/usr/bin/env python3
"""Independent decision model for the versioned Web routing policy."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src" / "main.cpp").read_text(encoding="utf-8")
HEADER = (ROOT / "include" / "routing_policy.h").read_text(encoding="utf-8")


def ga(main, middle=0, sub=0):
    assert 0 <= main <= 31 and 0 <= middle <= 7 and 0 <= sub <= 255
    return (main << 11) | (middle << 8) | sub


def allowed(mode, ranges, address):
    if mode == "all":
        return True
    if mode == "block":
        return False
    return any(first <= address <= last for first, last in ranges)


def bitmap(ranges):
    result = bytearray(8192)
    for first, last in ranges:
        for address in range(first, last + 1):
            result[address >> 3] |= 1 << (address & 7)
    return result


def compact(table):
    ranges, address = [], 0
    while address < 65536:
        if not table[address >> 3] & (1 << (address & 7)):
            address += 1
            continue
        first = address
        while address + 1 < 65536 and table[(address + 1) >> 3] & (1 << ((address + 1) & 7)):
            address += 1
        ranges.append((first, address))
        address += 1
    return ranges


ranges = [
    (ga(0, 0, 1), ga(0, 0, 10)),
    (ga(15), ga(16, 7, 255)),
    (ga(31, 0, 1), ga(31, 0, 1)),
]

assert allowed("filter", ranges, ga(0, 0, 1))
assert not allowed("filter", ranges, ga(0, 0, 11))
assert allowed("filter", ranges, ga(15, 7, 255))
assert allowed("filter", ranges, ga(16, 0, 0))
assert not allowed("filter", ranges, ga(30, 7, 255))
assert allowed("filter", ranges, ga(31, 0, 1))
assert allowed("all", [], ga(31, 7, 255))
assert not allowed("block", ranges, ga(0, 0, 1))


def topology(router, destination, ip_to_tp):
    assert router & 0xFF == 0
    area, line = router >> 12, (router >> 8) & 0xF
    d_area, d_line = destination >> 12, (destination >> 8) & 0xF
    below = (d_area == area and d_line == line) if line else d_area == area
    return below if ip_to_tp else not below


assert topology(0x2100, 0x212A, True)
assert not topology(0x2100, 0x2201, True)
assert topology(0x2100, 0x2201, False)
assert topology(0x2000, 0x2F01, True)
assert topology(0x2000, 0x3101, False)

assert len(bitmap([])) == 8192 and not any(bitmap([]))
assert all(value == 0xFF for value in bitmap([(0, 65535)]))
isolated = [(index * 2, index * 2) for index in range(100)]
assert compact(bitmap(isolated)) == isolated  # more than the former 64 ranges
assert compact(bitmap(ranges)) == ranges
assert "kBitmapBytes=kAddressCount/8" in HEADER
assert "kMaxImportBytes=12288" in HEADER
assert 'putBytes("routev2c"' in SOURCE
assert 'getBytesLength("routing2")' in SOURCE  # transient raw bitmap migration
assert 'getBytesLength("routing")' in SOURCE  # schema-v1 migration retained
assert "*candidate={}" not in SOURCE  # an 8 KiB aggregate temporary overflows loopTask
assert "memset(candidate,0,sizeof(*candidate))" in SOURCE
assert "UdpRxEvent& event=udpTaskRxEvent" in SOURCE
assert "destinationAddress()==0" in SOURCE
assert "routeFilterAllows(cemi,true" in SOURCE
assert "routeFilterAllows(cemi,false" in SOURCE
assert "if(!cemi.hopCount())" in SOURCE
assert "consumeFingerprint(recentTpTx" in SOURCE
assert "consumeFingerprint(recentIpTx" in SOURCE
assert "static_assert(ROUTING_ARMED==1" in SOURCE
assert "ipTpEnabled=false;ipTpPhase=IpTpPhase::Passive;clearRouteQueue()" in SOURCE
assert "productConfigPost" in SOURCE

print("OK: group 0/15/16/31 boundaries, modes, topology, broadcast gate, hop and echo guards")
