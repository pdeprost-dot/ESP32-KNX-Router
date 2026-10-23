#!/usr/bin/env python3
"""Offline wire checks for a fictitious KNX Ultimate TunnelUDP profile."""

from pathlib import Path


def fcs(data: bytes) -> int:
    value = 0xFF
    for byte in data:
        value ^= byte
    return value


node_red_address = 0x2121  # Fictitious documentation address 2.1.33.

# CONNECT_RESPONSE: channel 1, success, HPAI UDP, fictitious CRD address.
response = bytes.fromhex("06 10 02 06 00 14 01 00 08 01 C0 00 02 0A 0E 57 04 04 21 21")
assert len(response) == 20
assert response[2:4] == bytes.fromhex("02 06")
assert response[6:8] == bytes([1, 0])
assert response[16:20] == bytes([4, 4, node_red_address >> 8, node_red_address & 0xFF])

# KNX Ultimate GroupValueWrite OFF using the fictitious source address.
cemi = bytes.fromhex("11 00 BC E0 21 21 10 00 01 00 80")
tp_without_fcs = bytes.fromhex("BC 21 21 10 00 D1 00 80")
tp = tp_without_fcs + bytes([fcs(tp_without_fcs)])
assert tp == bytes.fromhex("BC 21 21 10 00 D1 00 80 02")
assert tp[1:3] == bytes.fromhex("21 21")
assert ((tp[5] >> 4) & 7) == 5

source = (Path(__file__).parents[1] / "src" / "main.cpp").read_text(encoding="utf-8")
assert "nodeRedTunnelMode=false" in source
assert "node_red_tunnel_enable" in source
assert "kTunnelSlots=5" in source
assert "if(slot.address&&!slot.connected)" in source
assert "type==3&&management.connected" in source
assert "uint16_t tunnelAddresses[kTunnelSlots]{}" in source
assert "destination==slot.address" in source
assert 'metric(r,"Verrou global ROUTING_ARMED",ROUTING_ARMED?"ARME":"DESACTIVE")' in source

print("OK: fictitious KNX Ultimate IA, generic slots, management separate, OFF vector")
