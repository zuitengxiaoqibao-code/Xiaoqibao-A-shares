import argparse
import logging
import multiprocessing
import os
from pathlib import Path
import subprocess
import time

from qibao_desktop.data_migration import (
    CURRENT_MIGRATION_VERSION,
    apply_migrations,
    promote_previous_data_layout,
)
from qibao_desktop.instance import (
    AlreadyRunningError,
    SingleInstance,
    activate_existing_window,
)
from qibao_desktop.logging_config import configure_desktop_logging
from qibao_desktop.paths import desktop_layout
from qibao_desktop.startup_progress import read_startup_progress
from qibao_desktop.window import run_window
from qibao_desktop.pending_update import load_pending_update


logger = logging.getLogger(__name__)


def _create_local_api_server(port: int):
    from qibao_desktop.server import LocalApiServer

    return LocalApiServer(
        app="qibao_api.main:app",
        port=port,
        startup_timeout=60,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xiaoqibao")
    parser.add_argument("--portable-root", type=Path)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--instance-name", default="xiaoqibao-portable")
    parser.add_argument("--apply-pending-update", type=Path)
    parser.add_argument("--parent-pid", type=int)
    return parser


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _run_update_helper(manifest: Path, parent_pid: int | None) -> int:
    update = load_pending_update(manifest, allowed_dist_root=update_dist_root(manifest))
    deadline = time.monotonic() + 30
    while parent_pid and _process_exists(parent_pid) and time.monotonic() < deadline:
        time.sleep(0.1)
    if parent_pid and _process_exists(parent_pid):
        return 3
    update.apply()
    manifest.unlink(missing_ok=True)
    subprocess.Popen([str(update.target_root / "xiaoqibao.exe")], cwd=update.target_root)
    return 0


def update_dist_root(manifest: Path) -> Path:
    return manifest.resolve().parent.parent


def _handoff_pending_update(portable_root: Path | None) -> bool:
    layout = desktop_layout(portable_root)
    manifest = layout.root / "pending-update.json"
    if not manifest.is_file():
        return False
    update = load_pending_update(manifest, allowed_dist_root=layout.root.parent)
    helper = update.staged_root / "xiaoqibao.exe"
    if not helper.is_file():
        logger.warning("pending update helper is missing: %s", helper)
        return False
    subprocess.Popen(
        [str(helper), "--apply-pending-update", str(manifest), "--parent-pid", str(os.getpid())],
        cwd=update.staged_root,
    )
    return True


def _prepare_runtime(portable_root: Path | None):
    layout = desktop_layout(portable_root)
    layout.ensure()
    configure_desktop_logging(layout.logs_dir)
    migration_version = apply_migrations(layout.root, CURRENT_MIGRATION_VERSION)
    logger.info("desktop startup stage=data-migrations-applied version=%s", migration_version)
    os.environ["QIBAO_PORTABLE_ROOT"] = str(layout.root)
    os.environ["QIBAO_DATA_DIR"] = str(layout.data_dir)
    os.environ["QIBAO_WEB_DIR"] = str(layout.web_dir)
    return layout


def main(argv: list[str] | None = None) -> int:
    multiprocessing.freeze_support()
    args = _parser().parse_args(argv)
    if args.apply_pending_update is not None:
        return _run_update_helper(args.apply_pending_update, args.parent_pid)
    server = None
    try:
        with SingleInstance(args.instance_name):
            if not args.headless and _handoff_pending_update(args.portable_root):
                return 0
            if args.headless:
                layout = _prepare_runtime(args.portable_root)
                promote_previous_data_layout(layout)
                server = _create_local_api_server(args.port)
                server.start()
                server.wait()
            else:
                # Prepare the portable paths and launch the API thread before
                # creating the webview.  The visible shell and Python API
                # import/initialization can then overlap instead of making the
                # user wait for the API after the window has appeared.
                layout = _prepare_runtime(args.portable_root)
                promote_previous_data_layout(layout)
                server = _create_local_api_server(args.port)
                server.launch()

                def start_application() -> str:
                    server.wait_until_ready()
                    return server.url

                run_window(
                    start_application,
                    startup_progress=lambda: read_startup_progress(
                        layout.logs_dir / "xiaoqibao.log"
                    ),
                )
        return 0
    except AlreadyRunningError:
        activated = activate_existing_window("一树电子商务-A股观测台")
        logger.warning("xiaoqibao is already running; activated=%s", activated)
        return 2
    except Exception:
        logger.exception("desktop startup failed")
        return 1
    finally:
        if server is not None:
            server.stop()
