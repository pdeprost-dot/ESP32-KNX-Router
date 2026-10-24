#!/usr/bin/env python3
"""Independent, bounded checks for the TP1 simulator frame gate."""

def expected_length(frame: bytes) -> int:
    if len(frame) < 7:
        return 0
    extended = (frame[0] & 0xD3) == 0x10
    return 9 + frame[6] if extended else 8 + (frame[5] & 0x0F)


def valid(frame: bytes) -> bool:
    value = 0
    for octet in frame:
        value ^= octet
    return len(frame) >= 8 and expected_length(frame) == len(frame) and value == 0xFF


def main() -> None:
    # Independently captured/validated short GroupValueWrite OFF frame.
    good = bytes.fromhex("BC 11 FD 10 00 E1 00 80 DE")
    assert valid(good)
    damaged = bytearray(good)
    damaged[-1] ^= 1
    assert not valid(damaged)
    assert not valid(good[:-1])
    print("PASS: TP length/FCS gate, invalid checksum and truncated frame")


if __name__ == "__main__":
    main()
