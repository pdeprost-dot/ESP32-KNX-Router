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

# ETS6 opens this separate two-byte CRI after its tunneling connection.
management_connect = (
    header(0x0205, 24)
    + hpai(client_ip, 41002)
    + hpai(client_ip, 41002)
    + bytes([2, 3])
)
assert len(management_connect) == 24
assert management_connect[22:] == bytes([2, 3])

management_response = (
    header(0x0206, 18)
    + bytes([2, 0])
    + hpai("192.0.2.156", 3671)
    + bytes([2, 3])
)
assert len(management_response) == 18
assert management_response[6] != response[6]  # distinct channel IDs
assert management_response[-2:] == bytes([2, 3])

ack = header(0x0421, 10) + bytes([4, 1, 0, 0])
assert len(ack) == 10 and ack[6:] == bytes([4, 1, 0, 0])

configuration_ack = header(0x0311, 10) + bytes([4, 2, 0, 0])
assert configuration_ack[7] == management_response[6]
assert configuration_ack[9] == 0

no_more_connections = header(0x0206, 8) + bytes([0, 0x24])
assert no_more_connections[-1] == 0x24

# ETS6 capture: unlike the 4-byte connection header used by tunneling and
# device-configuration packets, CONNECTIONSTATE/DISCONNECT carry their channel
# directly at byte 6. Byte 7 is reserved and was the source of stuck sessions.
state_request = bytes.fromhex("06 10 02 07 00 10 01 00 08 01 C0 A8 32 7B C9 CA")
disconnect_request = bytes.fromhex("06 10 02 09 00 10 02 00 08 01 C0 A8 32 7B C9 CA")
assert state_request[6] == 1 and state_request[7] == 0
assert disconnect_request[6] == 2 and disconnect_request[7] == 0
state_response = header(0x0208, 8) + bytes([state_request[6], 0])
disconnect_response = header(0x020A, 8) + bytes([disconnect_request[6], 0])
assert state_response == bytes.fromhex("06 10 02 08 00 08 01 00")
assert disconnect_response == bytes.fromhex("06 10 02 0A 00 08 02 00")

# A standard management request is transported unchanged after the connection header.
cemi = bytes.fromhex("11 00 BC E0 11 FE 11 01 60 03 00 80")
tunneling_request = header(0x0420, 10 + len(cemi)) + bytes([4, 1, 0, 0]) + cemi
assert tunneling_request[10:] == cemi
assert len(tunneling_request) == 10 + len(cemi)

print("OK: distinct channels, ETS state/disconnect offsets, ACKs, status 0x24 and cEMI")
