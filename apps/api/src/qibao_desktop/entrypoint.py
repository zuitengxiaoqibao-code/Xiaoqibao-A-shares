import argparse
import logging
import os
from pathlib import Path

from qibao_desktop.instance import AlreadyRunningError, SingleInstance
from qibao_desktop.logging_config import configure_desktop_logging
from qibao_desktop.paths import desktop_layout
from qibao_desktop.server import LocalApiServer
from qibao_desktop.window import run_window


logger = logging.getLogger(__name__)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xiaoqibao")
    parser.add_argument("--portable-root", type=Path)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--headless", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    layout = desktop_layout(args.portable_root)
    layout.ensure()
    configure_desktop_logging(layout.logs_dir)
    os.environ["QIBAO_PORTABLE_ROOT"] = str(layout.root)
    os.environ["QIBAO_DATA_DIR"] = str(layout.legacy_data_dir)
    os.environ["QIBAO_WEB_DIR"] = str(layout.web_dir)
    server = None
    try:
        with SingleInstance("xiaoqibao-portable"):
            server = LocalApiServer(
                app="qibao_api.main:app",
                port=args.port,
                startup_timeout=60,
            )
            server.start()
            if args.headless:
                server.wait()
            else:
                run_window(server.url)
        return 0
    except AlreadyRunningError:
        logger.warning("xiaoqibao is already running")
        return 2
    except Exception:
        logger.exception("desktop startup failed")
        return 1
    finally:
        if server is not None:
            server.stop()
