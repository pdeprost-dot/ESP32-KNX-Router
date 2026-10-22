#!/usr/bin/env python3
"""Poll bounded ESP32 runtime snapshots to rotating JSONL files on the PC."""

import argparse
import html
import json
from pathlib import Path
import re
import time
import urllib.request


METRICS = (
    "Heap libre (instantane)",
    "Plus grand bloc interne",
    "Marge pile loop/Web",
    "Marge pile tache UDP",
    "Marge pile tache NCN",
    "File RX pleine / capacite",
    "Erreurs lecture / surdimensionnes",
    "UDP TX succes / erreurs / reprises / pertes",
    "Octets UART TX / RX",
    "Erreurs parite / trame / debordement",
    "Journal UART ecrase / capacite",
    "File commandes / evenements perdues",
    "Trames completes / valides / invalides",
    "Tunnel 1",
    "Endpoint tunnel 1",
    "Compteurs tunnel 1",
    "Sequences tunnel 1",
    "Confirmations TP tunnel 1",
    "Tunnels connectes / refuses",
    "Tunnel DISCONNECT / expirations",
    "Indications IP / pertes TX",
    "Arbitre UART",
)


def fetch(url: str, timeout: float = 15.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "ESP-KNX bounded collector"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        return response.read()


def extract(page: str) -> dict[str, str]:
    values = {}
    for label in METRICS:
        pattern = re.escape(label) + r"</span><strong>(.*?)</strong>"
        match = re.search(pattern, page, re.DOTALL)
        if match:
            value = re.sub(r"<[^>]+>", " ", match.group(1))
            values[label] = " ".join(html.unescape(value).split())
    return values


def rotate(path: Path, maximum: int, copies: int) -> None:
    if not path.exists() or path.stat().st_size < maximum:
        return
    oldest = path.with_suffix(path.suffix + f".{copies}")
    oldest.unlink(missing_ok=True)
    for index in range(copies - 1, 0, -1):
        source = path.with_suffix(path.suffix + f".{index}")
        if source.exists():
            source.replace(path.with_suffix(path.suffix + f".{index + 1}"))
    path.replace(path.with_suffix(path.suffix + ".1"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.0.2.156")
    parser.add_argument("--interval", type=float, default=10.0)
    parser.add_argument("--duration", type=float, default=3600.0)
    parser.add_argument("--output", type=Path, default=Path("captures/knx-runtime.jsonl"))
    parser.add_argument("--max-bytes", type=int, default=2_000_000)
    parser.add_argument("--copies", type=int, default=3)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    sequence = 0
    while time.monotonic() - started < args.duration:
        record = {"sequence": sequence, "unix_time": time.time(), "elapsed_s": round(time.monotonic() - started, 3)}
        try:
            record["status"] = json.loads(fetch(f"http://{args.host}/api/status"))
            record["knx"] = extract(fetch(f"http://{args.host}/knx").decode("utf-8", "replace"))
            record["ok"] = True
        except Exception as error:  # collection must continue across brief Wi-Fi outages
            record["ok"] = False
            record["error"] = f"{type(error).__name__}: {error}"
        rotate(args.output, args.max_bytes, args.copies)
        with args.output.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        sequence += 1
        deadline = started + sequence * args.interval
        time.sleep(max(0.0, deadline - time.monotonic()))


if __name__ == "__main__":
    main()
