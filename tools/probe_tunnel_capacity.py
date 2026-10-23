#!/usr/bin/env python3
"""Open bounded KNXnet/IP sessions without sending any cEMI/TP request."""
import argparse
import socket
import struct


def header(service, length):
    return struct.pack("!BBHH", 6, 0x10, service, length)


def hpai(ip, port):
    return bytes([8, 1]) + socket.inet_aton(ip) + struct.pack("!H", port)


def request(sock, target, payload):
    sock.sendto(payload, target)
    data, peer = sock.recvfrom(512)
    return data, peer


def connect(sock, local_ip, target, kind):
    port = sock.getsockname()[1]
    cri = bytes([4, 4, 2, 0]) if kind == "tunnel" else bytes([2, 3])
    packet = header(0x0205, 22 + len(cri)) + hpai(local_ip, port) * 2 + cri
    data, peer = request(sock, target, packet)
    assert data[:4] == bytes.fromhex("06 10 02 06") and len(data) >= 8
    return data[6], data[7], data, peer


def disconnect(sock, local_ip, target, channel):
    port = sock.getsockname()[1]
    packet = header(0x0209, 16) + bytes([channel, 0]) + hpai(local_ip, port)
    data, _ = request(sock, target, packet)
    assert data == header(0x020A, 8) + bytes([channel, 0])


parser = argparse.ArgumentParser()
parser.add_argument("--target", default="192.0.2.156")
parser.add_argument("--local", required=True)
args = parser.parse_args()
target = (args.target, 3671)
sockets = []
try:
    for label, kind in (("tunnel-A", "tunnel"), ("tunnel-B", "tunnel"),
                        ("tunnel-refuse", "tunnel"), ("management", "management")):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)
        sock.bind((args.local, 0))
        sockets.append((sock, None, kind))
        channel, status, raw, peer = connect(sock, args.local, target, kind)
        print(f"{label}: peer={peer[0]}:{peer[1]} channel={channel} status=0x{status:02X} raw={raw.hex(' ')}")
        if label in ("tunnel-A", "tunnel-B", "management"):
            assert status == 0
            sockets[-1] = (sock, channel, kind)
        else:
            assert status == 0x24
            assert channel == 0
    channels = [channel for _, channel, _ in sockets if channel]
    assert len(channels) == len(set(channels))
finally:
    for sock, channel, _ in reversed(sockets):
        if channel:
            disconnect(sock, args.local, target, channel)
        sock.close()
print("OK: two additional tunnels and management coexisted; unavailable fourth tunnel refused; no cEMI sent")
