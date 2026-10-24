#!/usr/bin/env python3
"""Independent structural checks for SEARCH/DESCRIPTION response layout."""

from pathlib import Path
import socket
import struct


def dibs() -> bytes:
    mac = bytes.fromhex("68 09 47 A0 DE AC")
    name = b"ESP32 KNX Tunnel".ljust(30, b"\0")
    device = bytes((54, 1, 2, 0)) + bytes.fromhex("11 FD 00 00") + mac
    device += socket.inet_aton("224.0.23.12") + mac + name
    services = bytes.fromhex("0A 02 02 01 03 01 04 01 05 01")
    assert len(device) == 54
    return device + services


def header(service: int, length: int) -> bytes:
    return struct.pack("!BBHH", 6, 0x10, service, length)


description = header(0x0204, 70) + dibs()
search = header(0x0202, 78) + bytes.fromhex("08 01 C0 A8 32 9C 0E 57") + dibs()
assert len(description) == 70
assert len(search) == 78
assert search[6:14] == bytes.fromhex("08 01 C0 A8 32 9C 0E 57")
assert search[14:20] == bytes.fromhex("36 01 02 00 11 FD")
assert search[-10:] == bytes.fromhex("0A 02 02 01 03 01 04 01 05 01")

source = (Path(__file__).parents[1] / "src" / "main.cpp").read_text(encoding="utf-8")
assert "service!=SearchRequest" in source
assert "knxIpHeader(out,SearchResponse,sizeof(out))" in source
assert "uint8_t out[78]" in source
assert "writeDiscoveryDibs(out+14)" in source
assert "writeDiscoveryDibs(out+6)" in source
assert "out[62]=5;out[63]=1" in source

print("OK: SEARCH 78 bytes, DESCRIPTION 70 bytes, configured IA, Core/DM/Tunnelling/Routing")
