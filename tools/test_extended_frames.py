"""Independent KNX TP1 extended-frame reference vectors (no firmware imports)."""

MAX_TP = 263


def fcs(data):
    value = 0xFF
    for byte in data:
        value ^= byte
    return value


def make_extended(length):
    assert 9 <= length <= MAX_TP
    tp = bytearray(length)
    tp[0:7] = bytes((0x10, 0xE0, 0x11, 0xFD, 0x10, 0x00, length - 9))
    for index in range(7, length - 1):
        tp[index] = ((index * 37) ^ 0xCC) & 0xFF
    tp[-1] = fcs(tp[:-1])
    return tp


def tp_to_cemi(tp):
    assert len(tp) == 9 + tp[6]
    assert tp[-1] == fcs(tp[:-1])
    return bytearray((0x29, 0)) + tp[:-1]


def cemi_to_tp(cemi):
    assert len(cemi) == 10 + cemi[8]
    tp = bytearray(cemi[2:])
    tp.append(fcs(tp))
    return tp


def make_standard(apdu_length):
    assert 1 <= apdu_length <= 16
    tp = bytearray(7 + apdu_length)
    tp[0:5] = bytes((0xBC, 0x11, 0xFD, 0x10, 0x00))
    tp[5] = 0xE0 | (apdu_length - 1)
    for index in range(6, len(tp) - 1):
        tp[index] = ((index * 19) ^ 0x5A) & 0xFF
    tp[-1] = fcs(tp[:-1])
    return tp


def standard_tp_to_cemi(tp):
    count = tp[5] & 0x0F
    assert len(tp) == 8 + count and tp[-1] == fcs(tp[:-1])
    return bytearray((0x29, 0, tp[0], tp[5] & 0xF0)) + tp[1:5] + bytearray((count,)) + tp[6:-1]


def standard_cemi_to_tp(cemi):
    count = cemi[8]
    assert count <= 15 and len(cemi) == 10 + count
    tp = bytearray((cemi[2],)) + cemi[4:8] + bytearray(((cemi[3] & 0xF0) | count,)) + cemi[9:]
    tp.append(fcs(tp))
    return tp


def transport_commands(tp):
    result = []
    for index, byte in enumerate(tp):
        if index and index % 64 == 0:
            result.append(("offset", 0x08 | (index >> 6)))
        result.append(("service", (0x40 if index == len(tp) - 1 else 0x80) | (index & 0x3F)))
        result.append(("data", byte))
    return result


for boundary in (9, 31, 32, 33, 63, 64, 65, 127, 128, 129, 191, 192, 193, 263):
    original = make_extended(boundary)
    assert cemi_to_tp(tp_to_cemi(original)) == original

for apdu_length in (1, 2, 15, 16):
    original = make_standard(apdu_length)
    assert standard_cemi_to_tp(standard_tp_to_cemi(original)) == original

# Opaque payload: values which also occur as TPUART services or delimiters must
# survive unchanged. This is a transport test, not a Siemens Synco LTE test.
opaque = make_extended(129)
opaque[7:15] = bytes((0xCC, 0xCB, 0x09, 0x0A, 0x0B, 0x0C, 0x80, 0x40))
opaque[-1] = fcs(opaque[:-1])
assert cemi_to_tp(tp_to_cemi(opaque)) == opaque

maximum = make_extended(MAX_TP)
commands = transport_commands(maximum)
offsets = [value for kind, value in commands if kind == "offset"]
assert offsets == [0x09, 0x0A, 0x0B, 0x0C]
assert commands[-2] == ("service", 0x46)  # U_L_DataEnd, index 262 modulo 64.
assert maximum[-1] == fcs(maximum[:-1])

corrupt = bytearray(maximum)
corrupt[100] ^= 1
assert corrupt[-1] != fcs(corrupt[:-1])
assert len(maximum[:-1]) != 9 + maximum[6]

# Saturated and incoherent declared lengths are rejected by the reference
# invariants before any copy into a protocol queue.
assert len(maximum) == MAX_TP
assert len(maximum + b"\x00") > MAX_TP
bad_declared = bytearray(maximum)
bad_declared[6] -= 1
assert len(bad_declared) != 9 + bad_declared[6]

print("extended TP1 reference: boundaries, FCS, truncation and NCN offsets PASS")
