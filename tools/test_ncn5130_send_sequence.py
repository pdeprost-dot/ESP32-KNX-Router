"""Test hors ligne du Send Frame Service NCN5130, sans accès UART ni bus."""

TP_OFF = bytes.fromhex("BE 11 FD 10 00 E1 00 80 DC")


def encode_ncn5130(tp_frame: bytes) -> bytes:
    assert len(tp_frame) >= 7
    out = bytearray()
    for index, value in enumerate(tp_frame):
        if index == len(tp_frame) - 1:
            service = 0x40 | ((index + 1) & 0x3F)
        else:
            service = 0x80 | (index & 0x3F)
        out.extend((service, value))
    return bytes(out)


def main() -> None:
    assert len(TP_OFF) == 9
    checksum = 0
    for value in TP_OFF:
        checksum ^= value
    assert checksum == 0xFF
    expected = bytes.fromhex(
        "80 BE 81 11 82 FD 83 10 84 00 85 E1 86 00 87 80 49 DC"
    )
    actual = encode_ncn5130(TP_OFF)
    assert actual == expected
    assert actual[-2] == 0x49
    assert bytes.fromhex("48 DC") != actual[-2:]
    assert bytes((0x01, 0x02)) == bytes.fromhex("01 02")
    print("OK: TP=9 octets, XOR=FF, U_L_DataEnd=49, initialisation sans F1")


if __name__ == "__main__":
    main()
