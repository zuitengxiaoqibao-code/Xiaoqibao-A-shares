"""Create a data-free public snapshot from a verified portable build."""

import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import zipfile

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


ROOT = Path(__file__).resolve().parents[1]
PERSISTENT = {
    "config", "data", "news", "cache", "logs", "models", "exports", "backups",
}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checked_plan(source: Path, manifest: dict) -> list[tuple[Path, Path]]:
    plan = []
    seen = set()
    for entry in manifest["program_files"]:
        relative = PurePosixPath(entry["path"])
        if (not relative.parts or relative.is_absolute() or ".." in relative.parts
                or relative.parts[0] in PERSISTENT or "\\" in str(relative)
                or ":" in str(relative) or str(relative).casefold() in seen):
            raise ValueError(f"Unsafe or duplicate program path: {relative}")
        path = source.joinpath(*relative.parts)
        if not path.resolve().is_relative_to(source):
            raise ValueError(f"Program path escapes release: {relative}")
        if path.stat().st_size != entry["bytes"] or sha256(path).upper() != entry["sha256"].upper():
            raise ValueError(f"Program hash mismatch: {relative}")
        seen.add(str(relative).casefold())
        plan.append((path, Path(*relative.parts)))
    for required in ("xiaoqibao.exe", "web/index.html"):
        if required.casefold() not in seen:
            raise ValueError(f"Missing required program file: {required}")
    return plan


def python_notices(target: Path) -> list[dict]:
    pending = ["qibao-api", "pyinstaller"]
    visited = set()
    rows = []
    while pending:
        name = canonicalize_name(pending.pop())
        if name in visited:
            continue
        visited.add(name)
        distribution = metadata.distribution(name)
        for raw in distribution.requires or []:
            requirement = Requirement(raw)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                pending.append(requirement.name)
        if name == "qibao-api":
            continue
        destination = target / "python" / name
        destination.mkdir(parents=True, exist_ok=True)
        original_license = distribution.metadata.get("License", "")
        (destination / "METADATA.txt").write_text(
            distribution.read_text("METADATA") or "", encoding="utf-8",
        )
        for package_path in distribution.files or []:
            leaf = package_path.name.casefold()
            if not leaf.startswith(("license", "copying", "notice", "copyright", "authors")):
                continue
            original = distribution.locate_file(package_path)
            if original.is_file():
                safe_name = "__".join(p for p in package_path.parts if p not in ("..", "."))
                shutil.copy2(original, destination / safe_name)
        rows.append({
            "name": name, "version": distribution.version,
            "license_expression": distribution.metadata.get("License-Expression"),
            "license": original_license,
            "classifiers": [v for v in distribution.metadata.get_all("Classifier", [])
                            if v.startswith("License")],
            "project_urls": distribution.metadata.get_all("Project-URL", []),
        })
        # Ship the unmodified Python library sources for the bundled LGPL TTS.
        if name == "edge-tts":
            for package_path in distribution.files or []:
                if package_path.parts[0] == "edge_tts" and package_path.suffix == ".py":
                    source = distribution.locate_file(package_path)
                    output = target / "sources" / "edge-tts" / Path(*package_path.parts)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, output)
    return sorted(rows, key=lambda row: row["name"])


def frontend_notices(target: Path) -> list[dict]:
    rows = []
    modules = ROOT / "node_modules" / ".pnpm"
    for manifest in sorted(modules.glob("*/node_modules/*/package.json")) + sorted(
        modules.glob("*/node_modules/@*/*/package.json")
    ):
        package = json.loads(manifest.read_text(encoding="utf-8"))
        name, version = package.get("name", ""), package.get("version", "")
        if any(row["name"] == name and row["version"] == version for row in rows):
            continue
        destination = target / "javascript" / re.sub(r"[^a-zA-Z0-9._-]", "_", name + "-" + version)
        destination.mkdir(parents=True, exist_ok=True)
        for original in manifest.parent.iterdir():
            if original.is_file() and original.name.casefold().startswith(
                ("license", "licence", "notice", "copying", "copyright")
            ):
                shutil.copy2(original, destination / original.name)
        # The package manifest carries license and repository/source references.
        shutil.copy2(manifest, destination / "package.json")
        rows.append({"name": name, "version": version, "license": package.get("license"),
                     "repository": package.get("repository")})
    return sorted(rows, key=lambda row: (row["name"], row["version"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    target = ROOT / "release" / "XiaoQiBao-Portable"
    archive = ROOT / "release" / "XiaoQiBao-Portable-Windows-x64.zip"
    if target.exists() or archive.exists():
        raise SystemExit("Public release already exists; archive it outside the repository first.")
    manifest = json.loads((source / "release-manifest.json").read_text(encoding="utf-8-sig"))
    plan = checked_plan(source, manifest)
    # Check the full program before creating an output directory.
    target.mkdir(parents=True)
    for original, relative in plan:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, destination)
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, target / name)
    shutil.copy2(ROOT / "packaging" / "portable-program-readme.txt", target / "使用说明.txt")
    (target / "README.md").write_text(
        "# 易数智算 · A 股观测台\n\n"
        "完整解压后运行 xiaoqibao.exe，保留 _internal 和 web 目录。\n\n"
        "环境、首次使用、数据补齐与许可请阅读同目录的使用说明.txt 和 LICENSE。\n\n"
        "完整使用指南与源码部署：\n"
        "https://github.com/zuitengxiaoqibao-code/Xiaoqibao-A-shares#readme\n",
        encoding="utf-8",
    )
    # Do not copy the internal release manifest: it can contain local evidence.
    # These fields describe only the verified binary build.
    public = {
        "build_version": manifest["version"],
        "build_source_commit": manifest["commit"],
        "build_source_state": manifest.get("source_state", "unknown"),
        "exe_sha256": sha256(target / "xiaoqibao.exe"),
        "program_files_verified": len(plan),
        "persistent_data_included": False,
        "repository": "https://github.com/zuitengxiaoqibao-code/Xiaoqibao-A-shares",
        "python": sys.version.split()[0],
    }
    notices = target / "THIRD_PARTY_LICENSES"
    dependencies = {"python_runtime": python_notices(notices),
                    "javascript_build_environment": frontend_notices(notices)}
    (notices / "dependencies.json").write_text(
        json.dumps(dependencies, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    # Python's stdlib/runtime carries its own license, outside wheel metadata.
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        shutil.copy2(python_license, notices / "PYTHON-LICENSE.txt")
    (target / "PUBLIC-RELEASE.json").write_text(
        json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    hashes = [f"{sha256(path)}  {path.relative_to(target).as_posix()}"
              for path in sorted(target.rglob("*")) if path.is_file()]
    (target / "SHA256SUMS.txt").write_text("\n".join(hashes) + "\n", encoding="utf-8")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in sorted(target.rglob("*")):
            if path.is_file():
                output.write(path, (Path(target.name) / path.relative_to(target)).as_posix())
    if archive.stat().st_size >= 100 * 1024 * 1024:
        raise SystemExit("Archive exceeds GitHub's 100 MiB per-file limit; use a Release asset.")
    with zipfile.ZipFile(archive) as output:
        if output.testzip() is not None:
            raise RuntimeError("Archive CRC check failed")
        for path in sorted(target.rglob("*")):
            if path.is_file():
                relative = (Path(target.name) / path.relative_to(target)).as_posix()
                if hashlib.sha256(output.read(relative)).hexdigest() != sha256(path):
                    raise RuntimeError(f"Archive hash mismatch: {relative}")
    result = {**public, "archive": archive.name, "archive_bytes": archive.stat().st_size,
              "archive_sha256": sha256(archive),
              "python_dependency_count": len(dependencies["python_runtime"]),
              "javascript_package_count": len(dependencies["javascript_build_environment"])}
    (ROOT / "release" / "PUBLIC-DOWNLOAD.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
