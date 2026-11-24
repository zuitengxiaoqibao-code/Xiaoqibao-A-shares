"""Check program hashes and ensure a Program-Only ZIP has no user data."""
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile


def verify(release: Path, archive: Path):
    manifest = json.loads((release / "release-manifest.json").read_text(encoding="utf-8"))
    persistent = {"config", "data", "news", "cache", "logs", "models", "exports", "backups"}
    with ZipFile(archive) as source:
        assert source.testzip() is None, "ZIP CRC check failed"
        names = {item.replace("\\", "/"): item for item in source.namelist()}
        unexpected = [name for name in names if len(name.split("/")) > 2
                      and name.split("/")[1] in persistent and not name.endswith("/")]
        assert not unexpected, f"Unexpected user data: {unexpected}"
        checked = 0
        for entry in manifest["program_files"]:
            if entry["path"] == "release-manifest.json":
                continue
            path = "XiaoQiBao-Portable/" + entry["path"]
            assert path in names, f"Missing program file: {path}"
            digest = hashlib.sha256(source.read(names[path])).hexdigest().upper()
            assert digest == entry["sha256"].upper(), f"Hash mismatch: {path}"
            checked += 1
    print(json.dumps({"program_hashes_verified": checked, "user_data_files": 0,
        "exe_sha256": hashlib.sha256((release / "xiaoqibao.exe").read_bytes()).hexdigest().upper()}, indent=2))


if __name__ == "__main__":
    verify(Path(sys.argv[1]), Path(sys.argv[2]))
