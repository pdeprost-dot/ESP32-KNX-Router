#!/usr/bin/env python3
"""One bounded live tunnel request against a TP1-simulated development build."""
import argparse
import socket
import struct

def header(service, length): return struct.pack("!BBHH", 6, 0x10, service, length)
def hpai(ip, port): return bytes([8, 1]) + socket.inet_aton(ip) + struct.pack("!H", port)

p = argparse.ArgumentParser()
p.add_argument("--target", required=True)
p.add_argument("--local", required=True)
a = p.parse_args()
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(3)
s.bind((a.local, 0))
target = (a.target, 3671)
port = s.getsockname()[1]

connect = header(0x0205, 26) + hpai(a.local, port) * 2 + bytes([4, 4, 2, 0])
s.sendto(connect, target)
response, _ = s.recvfrom(512)
assert response[:6] == header(0x0206, len(response)) and response[7] == 0, response.hex(" ")
channel, assigned_hi, assigned_lo = response[6], response[-2], response[-1]

# L_data.req, assigned tunnel source, 2/0/0, GroupValueWrite OFF.
cemi = bytes([0x11, 0x00, 0xBC, 0xE0, assigned_hi, assigned_lo, 0x10, 0x00, 0x01, 0x00, 0x80])
request = header(0x0420, 10 + len(cemi)) + bytes([4, channel, 0, 0]) + cemi
s.sendto(request, target)
ack = None
confirmation = None
while ack is None or confirmation is None:
    packet, _ = s.recvfrom(512)
    service = struct.unpack("!H", packet[2:4])[0]
    if service == 0x0421:
        ack = packet
    elif service == 0x0420:
        confirmation = packet
        sequence = packet[8]
        s.sendto(header(0x0421, 10) + bytes([4, channel, sequence, 0]), target)

assert ack[6:10] == bytes([4, channel, 0, 0]), ack.hex(" ")
assert confirmation[10] == 0x2E, confirmation.hex(" ")  # L_data.con
disconnect = header(0x0209, 16) + bytes([channel, 0]) + hpai(a.local, port)
s.sendto(disconnect, target)
disconnected, _ = s.recvfrom(512)
assert disconnected == header(0x020A, 8) + bytes([channel, 0])
print(f"PASS channel={channel} address={assigned_hi >> 4}.{assigned_hi & 15}.{assigned_lo} ACK + simulated L_data.con + disconnect")
