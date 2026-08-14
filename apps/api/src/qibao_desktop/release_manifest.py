from collections.abc import Iterable, Mapping


def build_release_manifest(
    *,
    version: str,
    commit: str,
    dependency_lock_hash: str,
    migration_version: int,
    persistent_dirs: Iterable[str],
    program_files: Iterable[Mapping[str, object]],
    working_tree_dirty: bool = False,
) -> dict[str, object]:
    files = [dict(item) for item in program_files]
    program_hashes = [str(item["sha256"]) for item in files if item.get("sha256")]
    return {
        "version": version,
        "commit": commit,
        "source_state": "dirty" if working_tree_dirty else "clean",
        "working_tree_dirty": working_tree_dirty,
        "dependency_lock_hash": dependency_lock_hash,
        "migration_version": migration_version,
        "persistent_dirs": list(persistent_dirs),
        "program_files": files,
        "program_sha256": program_hashes[0] if len(program_hashes) == 1 else None,
    }
