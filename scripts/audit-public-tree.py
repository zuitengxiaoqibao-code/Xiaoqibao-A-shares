"""Audit Git-indexed public files without printing candidate secrets."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PREFIXES = (
    "docs/project-memory/", "docs/superpowers/", "docs/verification/",
    ".runtime/", ".venv/", "dist/", "build/", "node_modules/",
)
RUNTIME_DIRS = {"config", "data", "news", "cache", "logs", "models", "exports", "backups"}
SECRET_PATTERNS = {
    "private-key": re.compile(
        rb"-----BEGIN ((?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY)-----\r?\n"
        rb"[A-Za-z0-9+/=\r\n]{64,}-----END \1-----"
    ),
    "github-token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})"),
    "api-key": re.compile(rb"sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}"),
    "feishu-webhook": re.compile(rb"https://open.feishu.cn/open-apis/bot/v2/hook/[0-9a-f-]{30,}"),
}


def main() -> None:
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    paths = [p.decode("utf-8") for p in tracked.split(b"\0") if p]
    index = {}
    for row in subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=ROOT).split(b"\0"):
        if row:
            header, path = row.split(b"\t", 1)
            index[path.decode("utf-8")] = header.split()[1].decode("ascii")
    findings = []
    for relative in paths:
        path = ROOT / relative
        if relative.startswith(PRIVATE_PREFIXES):
            findings.append({"path": relative, "reason": "local-working-record-or-runtime"})
            continue
        parts = Path(relative).parts
        if parts[0] in RUNTIME_DIRS or (
            relative.startswith("release/XiaoQiBao-Portable/")
            and len(parts) > 2 and parts[2] in RUNTIME_DIRS
        ):
            findings.append({"path": relative, "reason": "runtime-data"})
        if not path.is_file():
            findings.append({"path": relative, "reason": "indexed-file-missing"})
            continue
        if path.stat().st_size >= 100 * 1024 * 1024:
            findings.append({"path": relative, "reason": "github-file-size-limit"})
        if path.suffix.casefold() in {".db", ".sqlite", ".sqlite3", ".duckdb", ".log", ".pfx", ".p12"}:
            findings.append({"path": relative, "reason": "database-log-or-credential-file"})
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
            findings.append({"path": relative, "reason": "environment-secrets"})
        if path.suffix.casefold() == ".zip":
            continue
        payload = path.read_bytes()
        if relative.startswith("release/XiaoQiBao-Portable/"):
            blob = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
            if blob != index[relative]:
                findings.append({"path": relative, "reason": "git-index-changes-release-bytes"})
        for name, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(payload):
                findings.append({"path": relative, "reason": name,
                                 "line": payload[:match.start()].count(b"\n") + 1})
    release = ROOT / "release" / "XiaoQiBao-Portable"
    count = 0
    for line in (release / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = release / relative
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            findings.append({"path": relative, "reason": "release-hash-mismatch"})
        count += 1
    with zipfile.ZipFile(ROOT / "release" / "XiaoQiBao-Portable-Windows-x64.zip") as archive:
        if archive.testzip() is not None:
            findings.append({"reason": "archive-crc"})
        for name in archive.namelist():
            parts = Path(name).parts
            if len(parts) > 1 and parts[1] in RUNTIME_DIRS:
                findings.append({"path": name, "reason": "archive-runtime-data"})
    print(json.dumps({"indexed_files": len(paths), "release_hashes_checked": count,
                      "findings": findings}, ensure_ascii=False, indent=2))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
