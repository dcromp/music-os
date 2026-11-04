"""Build a separate NNLS acoustic host from the existing reviewed native assets.

No plugin rebuild, downloads, global install, or changes to the Chordino host.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "experiments/candidate-assets"
PLUGIN_REVISION = "4c5f214a75cb354f8d8c933e161377c5b4d83713"
SDK_REVISION = "44c2487763eb248a933e9eff9169cfadee375009"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise SystemExit("This reviewed recipe targets Apple Silicon macOS")
    chordino_native = ASSETS / "chordino-native"
    original = json.loads((chordino_native / "buildinfo.json").read_text())
    plugin = chordino_native / "nnls-chroma.dylib"
    if original["plugin"]["revision"] != PLUGIN_REVISION:
        raise ValueError("Unreviewed NNLS plugin revision")
    if sha(plugin) != original["binaries"][plugin.name]["sha256"]:
        raise ValueError("NNLS plugin differs from its recorded build")
    sdk = ASSETS / "vamp-plugin-sdk"
    if original["vamp_sdk"]["revision"] != SDK_REVISION:
        raise ValueError("Unreviewed SDK revision")
    revision = subprocess.check_output(["git", "-C", str(sdk), "rev-parse", "HEAD"], text=True).strip()
    if revision != SDK_REVISION:
        raise ValueError("SDK checkout differs from reviewed revision")
    subprocess.run(["git", "-C", str(sdk), "diff", "--exit-code", "HEAD"], check=True)
    library = sdk / "build/libvamp-hostsdk.a"
    if not library.is_file():
        raise ValueError("Build reviewed native assets first: docs/CHORDINO_SETUP.md")
    source = Path(__file__).with_name("nnls-chroma-host.cpp")
    destination = ASSETS / "nnls-chroma-evidence-native"
    destination.mkdir(exist_ok=True)
    host = destination / "nnls-chroma-host"
    command = ["clang++", "-std=c++11", "-O3", "-arch", "arm64", "-mmacosx-version-min=11.0",
               "-I", str(sdk), str(source), str(library), "-o", str(host)]
    subprocess.run(command, check=True)
    info = {
        "schema_version": "1.0", "candidate": "nnls-chroma-acoustic-evidence",
        "architecture": "arm64", "minimum_macos": "11.0",
        "plugin": original["plugin"], "vamp_sdk": original["vamp_sdk"],
        "plugin_binary_sha256": sha(plugin), "host_binary_sha256": sha(host),
        "host_source_sha256": sha(source), "sdk_static_library_sha256": sha(library),
        "sdk_library_reuse": "already-built reviewed Chordino SDK assets; library hash captured here",
        "compiler": subprocess.check_output(["clang++", "--version"], text=True).splitlines()[0],
        "build_command": command,
        "host_semantics": {"plugin_key": "nnls-chroma:nnls-chroma", "output": "chroma",
                           "timestamp_method": "ShiftData", "timestamp_adjustment_seconds": 0,
                           "window": "Hann", "block_size": 16384, "hop_size": 2048,
                           "timestamps": "frame centers; zero padding at recording edges",
                           "native_bins": ["A", "Bb", "B", "C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab"]},
    }
    (destination / "buildinfo.json").write_text(json.dumps(info, indent=2) + "\n")
    print(f"Built separate acoustic host in {destination}")


if __name__ == "__main__":
    main()
