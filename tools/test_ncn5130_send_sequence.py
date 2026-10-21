"""Références indépendantes pour la future séquence NCN5130, sans UART."""

CAPTURED_CEMI = bytes.fromhex("29 00 BC D0 11 0B 10 0A 01 00 80")
CAPTURED_TP = bytes.fromhex("BC 11 0B 10 0A E1 00 80 22")
CANDIDATE_TP = bytes.fromhex("BC 11 FD 10 00 E1 00 80 DE")
CANDIDATE_SERVICES = bytes.fromhex(
    "80 BC 81 11 82 FD 83 10 84 00 85 E1 86 00 87 80 48 DE"
)


def xor_all(data: bytes) -> int:
    value = 0
    for octet in data:
        value ^= octet
    return value


def main() -> None:
    assert CAPTURED_CEMI[2] == CAPTURED_TP[0] == 0xBC
    assert CAPTURED_CEMI[4:8] == CAPTURED_TP[1:5]
    assert CAPTURED_TP[5:8] == bytes.fromhex("E1 00 80")
    assert xor_all(CAPTURED_TP) == 0xFF
    assert (0xBE ^ CAPTURED_TP[0]) == 0x02
    assert CANDIDATE_TP[0] == 0xBC
    assert xor_all(CANDIDATE_TP) == 0xFF
    assert CANDIDATE_SERVICES[-2:] == bytes.fromhex("48 DE")
    assert CANDIDATE_SERVICES[0::2] == bytes.fromhex(
        "80 81 82 83 84 85 86 87 48"
    )
    assert CANDIDATE_SERVICES[1::2] == CANDIDATE_TP
    print("OK: référence capturée BC, FCS DE, DataEnd 48, aucun accès matériel")


if __name__ == "__main__":
    main()
