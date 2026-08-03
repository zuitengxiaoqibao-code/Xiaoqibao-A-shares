import shutil
from datetime import datetime, timezone

from qibao_api.runtime.layout import RuntimeLayout


def promote_previous_data_layout(layout: RuntimeLayout) -> None:
    previous = layout.previous_data_dir
    if not previous.is_dir():
        return

    archive_root = None
    for source in sorted(previous.iterdir(), key=lambda path: path.name):
        target = layout.data_dir / source.name
        if target.exists():
            if archive_root is None:
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                archive_root = layout.backups_dir / f"previous-data-{stamp}"
                archive_root.mkdir(parents=True, exist_ok=False)
            shutil.move(str(source), str(archive_root / source.name))
        else:
            shutil.move(str(source), str(target))

    previous.rmdir()
