"""Reference independante de la conversion de validation IP vers TP."""

# ROUTING_INDICATION emise par le PC : 15.15.254 -> 2/0/0, GroupValueWrite OFF,
# compteur IP 6. Le controle cEMI demande un ACK au routeur IP; ce bit ne doit
# pas devenir le bit reserve du controle TP.
KNX_IP = bytes.fromhex(
    "06 10 05 30 00 11 29 00 BE E0 FF FE 10 00 01 00 80"
)
EXPECTED_TP = bytes.fromhex("BC FF FE 10 00 D1 00 80 03")
EXPECTED_TPUART = bytes.fromhex(
    "80 BC 81 FF 82 FE 83 10 84 00 85 D1 86 00 87 80 48 03"
)


def xor_all(data: bytes) -> int:
    value = 0
    for octet in data:
        value ^= octet
    return value


def main() -> None:
    assert KNX_IP[:6] == bytes.fromhex("06 10 05 30 00 11")
    cemi = KNX_IP[6:]
    assert cemi[0] == 0x29 and cemi[1] == 0
    assert cemi[2] == 0xBE                 # controle cEMI recu
    assert cemi[3] == 0xE0                 # groupe, hop=6
    assert cemi[4:8] == bytes.fromhex("FF FE 10 00")
    assert cemi[8:] == bytes.fromhex("01 00 80")
    assert EXPECTED_TP[0] == (cemi[2] & ~0x02)  # AckRequested cEMI retire
    assert EXPECTED_TP[1:5] == cemi[4:8]        # source et destination preservees
    assert EXPECTED_TP[5] == 0xD1               # groupe, hop 6 -> 5, longueur 1
    assert EXPECTED_TP[6:8] == cemi[9:11]       # APDU GroupValueWrite OFF
    assert xor_all(EXPECTED_TP) == 0xFF
    assert EXPECTED_TPUART[0::2] == bytes.fromhex(
        "80 81 82 83 84 85 86 87 48"
    )
    assert EXPECTED_TPUART[1::2] == EXPECTED_TP
    print("OK: source preservee, hop 6->5, controle BC, FCS 03, DataEnd 48")


if __name__ == "__main__":
    main()
