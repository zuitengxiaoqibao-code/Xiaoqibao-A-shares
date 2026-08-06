import argparse
import logging
import os
from pathlib import Path

from qibao_desktop.data_migration import promote_previous_data_layout
from qibao_desktop.instance import (
    AlreadyRunningError,
    SingleInstance,
    activate_existing_window,
)
from qibao_desktop.logging_config import configure_desktop_logging
from qibao_desktop.paths import desktop_layout
from qibao_desktop.window import run_window


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
    return parser


def _prepare_runtime(portable_root: Path | None):
    layout = desktop_layout(portable_root)
    layout.ensure()
    configure_desktop_logging(layout.logs_dir)
    os.environ["QIBAO_PORTABLE_ROOT"] = str(layout.root)
    os.environ["QIBAO_DATA_DIR"] = str(layout.data_dir)
    os.environ["QIBAO_WEB_DIR"] = str(layout.web_dir)
    return layout


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    server = None
    try:
        with SingleInstance("xiaoqibao-portable"):
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

                run_window(start_application)
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
