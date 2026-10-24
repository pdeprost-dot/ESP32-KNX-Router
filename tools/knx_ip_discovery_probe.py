#!/usr/bin/env python3
"""Bounded KNXnet/IP SEARCH/DESCRIPTION probe with structural decoding."""

import argparse
import ipaddress
import socket
import struct
import time


def hpai(address: str, port: int) -> bytes:
    return bytes((8, 1)) + socket.inet_aton(address) + struct.pack("!H", port)


def frame(service: int, payload: bytes) -> bytes:
    return struct.pack("!BBHH", 6, 0x10, service, len(payload) + 6) + payload


def decode(data: bytes, peer: tuple[str, int]) -> None:
    print(f"RX {len(data)} bytes from {peer[0]}:{peer[1]}: {data.hex(' ').upper()}")
    if len(data) < 6:
        print("  invalid: shorter than KNXnet/IP header")
        return
    header_len, version, service, declared = struct.unpack("!BBHH", data[:6])
    print(f"  header={header_len} version=0x{version:02X} service=0x{service:04X} declared={declared}")
    if header_len != 6 or version != 0x10 or declared != len(data):
        print("  invalid header or length")
        return
    offset = 6
    if service == 0x0202:
        if len(data) < 14 or data[6:8] != bytes((8, 1)):
            print("  invalid SEARCH_RESPONSE HPAI")
            return
        print(f"  endpoint={socket.inet_ntoa(data[8:12])}:{struct.unpack('!H', data[12:14])[0]}")
        offset = 14
    if service not in (0x0202, 0x0204):
        return
    while offset < len(data):
        if offset + 2 > len(data) or data[offset] < 2 or offset + data[offset] > len(data):
            print(f"  invalid DIB at offset {offset}")
            return
        length, dib_type = data[offset], data[offset + 1]
        dib = data[offset : offset + length]
        print(f"  DIB type=0x{dib_type:02X} length={length}: {dib.hex(' ').upper()}")
        if dib_type == 1 and length == 54:
            ia = struct.unpack("!H", dib[4:6])[0]
            name = dib[24:54].split(b"\0", 1)[0].decode("ascii", "replace")
            print(f"    medium=0x{dib[2]:02X} status=0x{dib[3]:02X} IA={(ia >> 12) & 15}.{(ia >> 8) & 15}.{ia & 255} name={name!r}")
        elif dib_type == 2 and length >= 2 and not (length % 2):
            families = [f"0x{dib[i]:02X}/v{dib[i+1]}" for i in range(2, length, 2)]
            print("    families=" + ", ".join(families))
        offset += length
    print("  structure complete")


def route_address(target: str) -> str:
    """Return the local IPv4 selected by the OS route to target."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect((target, 3671))
        return probe.getsockname()[0]
    finally:
        probe.close()


def request(target: str, service: int, timeout: float) -> bool:
    multicast = ipaddress.ip_address(target).is_multicast
    local_ip = route_address(target)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((local_ip, 0))
    if multicast:
        # A connected UDP socket would only accept datagrams from the multicast
        # peer. KNXnet/IP SEARCH_RESPONSE is instead sent as unicast by each
        # discovered server, so keep this socket deliberately unconnected.
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(local_ip))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    local_port = sock.getsockname()[1]
    packet = frame(service, hpai(local_ip, local_port))
    print(f"TX service=0x{service:04X} {local_ip}:{local_port} -> {target}:3671: {packet.hex(' ').upper()}")
    sock.sendto(packet, (target, 3671))
    deadline = time.monotonic() + timeout
    responders: set[tuple[str, int]] = set()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        sock.settimeout(remaining)
        try:
            data, peer = sock.recvfrom(2048)
        except socket.timeout:
            break
        responders.add(peer)
        decode(data, peer)
        if not multicast:
            break
    sock.close()
    if not responders:
        print("  timeout")
        return False
    print(f"  responders={len(responders)}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="192.0.2.10")
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args()
    search = request(args.target, 0x0201, args.timeout)
    description = request(args.target, 0x0203, args.timeout)
    raise SystemExit(0 if description else 1)


if __name__ == "__main__":
    main()
