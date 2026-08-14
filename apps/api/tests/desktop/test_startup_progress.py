from pathlib import Path

from qibao_desktop.startup_progress import read_startup_progress


def test_startup_progress_uses_latest_verified_milestone(tmp_path: Path) -> None:
    log = tmp_path / "xiaoqibao.log"
    log.write_text(
        "\n".join([
            "2026-08-07 INFO desktop startup stage=local-sources-ready elapsed_ms=437",
            "2026-08-07 INFO desktop startup stage=repositories-ready elapsed_ms=687",
            "2026-08-07 INFO desktop startup stage=market-sentiment-ready elapsed_ms=828",
        ]),
        encoding="utf-8",
    )

    progress = read_startup_progress(log)

    assert progress is not None
    assert progress.stage == "market-sentiment-ready"
    assert progress.percent == 38
    assert progress.step == "市场情绪服务已就绪"
    assert progress.detail == "正在准备首页与量化服务"


def test_startup_progress_exposes_elapsed_milliseconds_when_logged(tmp_path: Path) -> None:
    log = tmp_path / "xiaoqibao.log"
    log.write_text(
        "2026-08-11 INFO desktop startup stage=market-sentiment-ready elapsed_ms=828\n",
        encoding="utf-8",
    )

    progress = read_startup_progress(log)

    assert progress is not None
    assert progress.elapsed_ms == 828


def test_startup_progress_ignores_unknown_or_incomplete_log(tmp_path: Path) -> None:
    log = tmp_path / "xiaoqibao.log"
    log.write_text(
        "启动日志\n"
        "2026-08-07 INFO desktop startup stage=unknown elapsed_ms=12\n"
        "2026-08-07 INFO desktop startup stage=services-and-instrument-directory\n",
        encoding="utf-8",
    )

    assert read_startup_progress(log) is None


def test_startup_progress_reads_recent_tail_without_scanning_old_log(tmp_path: Path) -> None:
    log = tmp_path / "xiaoqibao.log"
    log.write_bytes(
        (b"old startup noise\n" * 50000)
        + b"2026-08-07 INFO desktop startup stage=lifespan-ready elapsed_ms=828\n"
    )

    progress = read_startup_progress(log)

    assert progress is not None
    assert progress.stage == "lifespan-ready"
