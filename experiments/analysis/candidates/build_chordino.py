"""Build the reviewed Chordino sources locally on Apple Silicon; no downloads."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "experiments/candidate-assets"
PLUGIN_REVISION = "4c5f214a75cb354f8d8c933e161377c5b4d83713"
SDK_REVISION = "44c2487763eb248a933e9eff9169cfadee375009"
BOOST_SHA = "f55c340aa49763b1925ccf02b2e83f35fdcf634c9d5164a2acb87540173c741d"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise SystemExit("This build recipe is for Apple Silicon macOS; other platforms need a separate recipe")
    plugin, sdk = (ASSETS / name for name in ("nnls-chroma", "vamp-plugin-sdk"))
    for repository, revision in ((plugin, PLUGIN_REVISION), (sdk, SDK_REVISION)):
        actual = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip()
        if actual != revision:
            raise ValueError(f"Expected {repository.name} source {revision}, found {actual}")
        subprocess.run(["git", "-C", str(repository), "diff", "--exit-code", "HEAD"], check=True)
    archive = ASSETS / "boost_1_87_0.tar.gz"
    if not archive.is_file() or sha(archive) != BOOST_SHA:
        raise ValueError("Fetch the hash-verified Boost 1.87.0 archive as described in docs/CHORDINO_SETUP.md")
    # Always build from the verified archive, never a potentially stale extracted tree.
    with tempfile.TemporaryDirectory(prefix="chordino-boost-", dir=ASSETS) as folder:
        with tarfile.open(archive, "r:gz") as source:
            members = [member for member in source.getmembers()
                       if member.name.startswith("boost_1_87_0/boost/")
                       or member.name in ("boost_1_87_0/boost", "boost_1_87_0/LICENSE_1_0.txt")]
            source.extractall(folder, members=members, filter="data")
        build(plugin, sdk, Path(folder) / "boost_1_87_0")


def build(plugin: Path, sdk: Path, boost: Path) -> None:
    native = ASSETS / "chordino-native"
    native.mkdir(exist_ok=True)
    host_source = Path(__file__).with_name("chordino-host.cpp")
    shutil.copy2(host_source, native / host_source.name)
    commands = [
        (sdk, ["cmake", "-S", ".", "-B", "build", "-DCMAKE_BUILD_TYPE=Release",
               "-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0", "-DCMAKE_OSX_ARCHITECTURES=arm64", "-DVAMPSDK_ENABLE_INSTALL=OFF"]),
        (sdk, ["cmake", "--build", "build", "--parallel", "4"]),
        (plugin, ["make", "-f", "Makefile.osx", "-B", "-j4", "CXX=clang++", "CC=clang",
                  "VAMP_SDK_DIR=../vamp-plugin-sdk", f"BOOST_ROOT={boost}",
                  "ARCHFLAGS=-mmacosx-version-min=11.0 -arch arm64", "OPTFLAGS=-O3",
                  "LDFLAGS=-mmacosx-version-min=11.0 -arch arm64 -dynamiclib -install_name nnls-chroma.dylib ../vamp-plugin-sdk/build/libvamp-sdk.a -exported_symbols_list vamp-plugin.list -framework Accelerate"]),
        (ASSETS, ["clang++", "-std=c++11", "-O3", "-arch", "arm64", "-mmacosx-version-min=11.0",
                  "-I", str(sdk), str(host_source), str(sdk / "build/libvamp-hostsdk.a"),
                  "-o", str(native / "chordino-host")]),
    ]
    for directory, command in commands:
        subprocess.run(command, cwd=directory, check=True)
    shutil.copy2(plugin / "nnls-chroma.dylib", native / "nnls-chroma.dylib")
    info = {
        "schema_version": "1.0", "candidate": "chordino", "architecture": "arm64", "minimum_macos": "11.0",
        "plugin": {"source_url": "https://github.com/c4dm/nnls-chroma", "revision": PLUGIN_REVISION,
                   "vamp_plugin_version": 5, "license": "GPL-2.0-or-later",
                   "dictionary": "upstream built-in; no external chord.dict"},
        "vamp_sdk": {"source_url": "https://github.com/vamp-plugins/vamp-plugin-sdk", "revision": SDK_REVISION,
                     "version": "2.10", "license": "COPYING: MIT-style permission notice plus name-promotion restriction; embedded KissFFT BSD-3-Clause"},
        "boost": {"source_url": "https://archives.boost.io/release/1.87.0/source/boost_1_87_0.tar.gz",
                  "version": "1.87.0", "archive_sha256": BOOST_SHA, "license": "BSL-1.0",
                  "usage": "header-only plugin dependency; freshly extracted from verified archive for every build"},
        "binaries": {name: {"sha256": sha(native / name)} for name in ("chordino-host", "nnls-chroma.dylib")},
        "host_source": {"filename": host_source.name, "sha256": sha(host_source)},
        "compiler": subprocess.check_output(["clang++", "--version"], text=True).splitlines()[0],
        "build_commands": [{"cwd": str(directory.relative_to(ASSETS)), "argv": command} for directory, command in commands],
        "host_semantics": {"input": "RIFF PCM16 mono WAV; 8000-192000 Hz; 512 MiB maximum",
                           "output": "# JSON metadata header, then seconds TAB native_label",
                           "timestamp_method": "ShiftData", "window": "Hann", "block_size": 16384,
                           "hop_size": 2048, "final_N_is_termination_marker": True},
    }
    (native / "buildinfo.json").write_text(json.dumps(info, indent=2) + "\n")
    print(f"Built native candidate in {native}")


if __name__ == "__main__":
    main()
