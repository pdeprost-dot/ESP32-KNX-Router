#!/usr/bin/env python3
"""Static installer-UI safety and information architecture checks."""

from pathlib import Path

root = Path(__file__).parents[1]
source = (root / "src" / "main.cpp").read_text(encoding="utf-8")
config = (root / "include" / "router_config.h").read_text(encoding="utf-8")

for route in ("/knx-advanced", "/knx-maintenance", "/knx-help"):
    assert route in source
assert '"/knx",knxPage' in source
assert '"/knx-config",installerConfigPage' in source
assert '"/knx-advanced","/knx?view=advanced"' in source
assert '"/knx-maintenance","/knx?view=maintenance"' in source
assert '"/knx-help","/knx?view=help"' in source
assert "Période des compteurs" in source
assert "Les périmètres sont distincts" in source
assert "Non configuré" in source
assert "Activer le routage configure" in source
assert "Desactiver le routage" in source
assert "Enregistrer la configuration" in source
assert "Confirmer l'absence de chemin de routage parallele" in source
assert "KNX_DEVELOPMENT_TOOLS 0" in config
assert "Outil de banc absent du firmware installateur" in source
assert "Comparaison inactive ou absence de correspondance non concluante" in source
assert "Rotation journal TP" in source
assert "Table vide = aucun groupe" in source
assert "0/0/0-31/7/255" in source
assert "Import limite a 12 288 octets" in source
assert "Le filtrage du routing ne s'applique pas aux tunnels" in source
assert "tunnel.enabled||ipTpEnabled" in source

summary = source[source.index("void statePage"):source.index("void advancedPage")]
assert " us" not in summary and "microseconde" not in summary
assert "U_Reset" not in summary and "UART" not in summary

print("OK: installer summary, configuration, help, maintenance and dev-tool gate")
