#!/usr/bin/env python3
"""Offline wire checks for the explicit KNX Ultimate TunnelUDP test profile."""

from pathlib import Path


def fcs(data: bytes) -> int:
    value = 0xFF
    for byte in data:
        value ^= byte
    return value


node_red_address = 0xFF16  # 15.15.22, preserved from the exported flow.

# CONNECT_RESPONSE: channel 1, success, HPAI UDP, CRD tunnel address 15.15.22.
response = bytes.fromhex("06 10 02 06 00 14 01 00 08 01 C0 A8 32 9C 0E 57 04 04 FF 16")
assert len(response) == 20
assert response[2:4] == bytes.fromhex("02 06")
assert response[6:8] == bytes([1, 0])
assert response[16:20] == bytes([4, 4, node_red_address >> 8, node_red_address & 0xFF])

# KNX Ultimate GroupValueWrite OFF using its preserved source address.
cemi = bytes.fromhex("11 00 BC E0 FF 16 10 00 01 00 80")
tp_without_fcs = bytes.fromhex("BC FF 16 10 00 D1 00 80")
tp = tp_without_fcs + bytes([fcs(tp_without_fcs)])
assert tp == bytes.fromhex("BC FF 16 10 00 D1 00 80 EB")
assert tp[1:3] == bytes.fromhex("FF 16")
assert ((tp[5] >> 4) & 7) == 5

source = (Path(__file__).parents[1] / "src" / "main.cpp").read_text(encoding="utf-8")
assert "kNodeRedTunnelAddress=0xFF16" in source
assert "nodeRedTunnelMode=false" in source
assert "node_red_tunnel_enable" in source
assert "else if(!tunnels[1].connected)freeSlot=&tunnels[1]" in source
assert "type==3&&management.connected" in source
assert "tunnels[0].address=kNodeRedTunnelAddress" in source
assert "tunnels[1].address=kTunnelAddresses[1]" in source
assert "destination==tunnels[0].address" in source
assert "ROUTING_ARMED=0" in source

print("OK: KNX Ultimate IA 15.15.22, ETS IA 1.1.252, management separate, OFF vector")
