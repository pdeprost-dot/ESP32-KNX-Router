#!/usr/bin/env python3
"""Independent checks for the NCN5130 TP receive framing rules used by v0.8.0."""


def fcs(data: bytes) -> int:
    value = 0
    for byte in data:
        value ^= byte
    return value ^ 0xFF


def expected_length(header: bytes) -> int:
    assert len(header) >= 7
    extended = (header[0] & 0xD3) == 0x10
    return 9 + header[6] if extended else 8 + (header[5] & 0x0F)


def split_tp(stream: bytes):
    frames = []
    offset = 0
    while offset < len(stream):
        if (stream[offset] & 0x33) == 0:
            offset += 1
            continue
        assert len(stream) - offset >= 7
        size = expected_length(stream[offset : offset + 7])
        frame = stream[offset : offset + size]
        assert len(frame) == size
        assert fcs(frame[:-1]) == frame[-1]
        frames.append(frame)
        offset += size
    return frames


def with_fcs(data):
    raw = bytes(data)
    return raw + bytes([fcs(raw)])


captured_a = bytes.fromhex("BC 11 0A 08 0A E1 00 81 3A")
captured_b = bytes.fromhex("BC 11 DB 09 1E E1 00 81 FE")
assert expected_length(captured_a[:7]) == 9
assert split_tp(captured_a + b"\xCC" + captured_b) == [captured_a, captured_b]

# CC is legal payload data and must not be treated as a frame delimiter.
payload_cc = with_fcs([0xBC, 0x11, 0x0A, 0x08, 0x0A, 0xE2, 0x00, 0x80, 0xCC])
assert expected_length(payload_cc[:7]) == 10
assert split_tp(payload_cc) == [payload_cc]

# Extended frames use the NPDU length byte at offset 6.
extended = with_fcs([0x10, 0x80, 0x11, 0x0A, 0x08, 0x0A, 0x02, 0x00, 0x81, 0x55])
assert expected_length(extended[:7]) == 11
assert split_tp(extended) == [extended]

print("OK: standard, back-to-back, embedded CC and extended TP frames")
