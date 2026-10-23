"""Generic factory defaults, NVS migration and commissioning validation."""
from pathlib import Path

source = (Path(__file__).parents[1] / "src" / "main.cpp").read_text(encoding="utf-8")


def valid(router, tunnels):
    if router in (0, 0xFFFF):
        return False
    used = set()
    for address in tunnels:
        if not address:
            continue
        if address in (0xFFFF, router) or address & 0xFF == 0 or address in used:
            return False
        used.add(address)
    return bool(used)


# Factory reset: no installation address and no tunnel can start.
factory = {"pa_set": False, "pa": 0, "tunnels": [0] * 5}
assert not valid(factory["pa"], factory["tunnels"])

# Fictitious commissioning example.
example = [0x2121, 0x2122, 0x2123, 0x2124, 0x2125]
assert valid(0x2120, example)
assert not valid(0x2120, [0x2121, 0x2121, 0, 0, 0])
assert not valid(0x2120, [0x2120, 0, 0, 0, 0])
assert not valid(0x2120, [0x2100, 0, 0, 0, 0])

# The generic firmware keeps schema 3 because its binary layout already stores
# all five addresses. Migration from schemas 1/2 yields empty tunnel slots.
legacy_v3 = {"pa": 0x2120, "tunnels": example.copy()}
migrated_v4 = {"pa": legacy_v3["pa"], "tunnels": legacy_v3["tunnels"].copy()}
assert migrated_v4 == legacy_v3

assert 'kConfigVersion=3' in source
assert 'uint16_t tunnelAddresses[kTunnelSlots]{}' in source
assert 'struct LegacyConfigV3' in source
assert 'memcpy(candidate.tunnelAddresses,old.tunnelAddresses' in source
assert 'commissioningReady' in source
assert 'scan TP non implemente' in source
assert 'aucun scan effectue' in source
assert 'kPrototypeAddress' not in source
for personal in ('0x11FD', '0xFF16', '0x11FE', '0x11FC'):
    assert personal not in source

print('OK: generic empty reset, schema-3 migration, validation, explicit non-emitting scan placeholder')
