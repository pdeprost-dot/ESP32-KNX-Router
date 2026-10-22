#!/usr/bin/env python3
"""Independent wire-format checks for the single-session ETS6 tunnel."""

import struct


def header(service: int, length: int) -> bytes:
    return struct.pack("!BBHH", 6, 0x10, service, length)


def hpai(ip: str, port: int) -> bytes:
    octets = bytes(map(int, ip.split(".")))
    return bytes([8, 1]) + octets + struct.pack("!H", port)


client_ip = "192.0.2.123"
connect = header(0x0205, 26) + hpai(client_ip, 41000) + hpai(client_ip, 41001) + bytes([4, 4, 2, 0])
assert len(connect) == 26
assert connect[23] == 4 and connect[24] == 2

response = (
    header(0x0206, 20)
    + bytes([1, 0])
    + hpai("192.0.2.156", 3671)
    + bytes([4, 4, 0x11, 0xFE])
)
assert len(response) == 20
assert response[-2:] == bytes.fromhex("11 FE")  # 1.1.254

ack = header(0x0421, 10) + bytes([4, 1, 0, 0])
assert len(ack) == 10 and ack[6:] == bytes([4, 1, 0, 0])

# A standard management request is transported unchanged after the connection header.
cemi = bytes.fromhex("11 00 BC E0 11 FE 11 01 60 03 00 80")
tunneling_request = header(0x0420, 10 + len(cemi)) + bytes([4, 1, 0, 0]) + cemi
assert tunneling_request[10:] == cemi
assert len(tunneling_request) == 10 + len(cemi)

print("OK: CONNECT, CRD 1.1.254, TUNNELING_ACK and transparent cEMI payload")
