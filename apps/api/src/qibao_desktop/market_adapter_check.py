"""Offline check for dynamically imported adapters inside the frozen EXE."""
import json
from importlib.metadata import version
from pathlib import Path
from time import perf_counter


def check_market_adapters(output: Path, *, online: bool = False) -> int:
    report = {}
    for package in ("eltdx", "axdata"):
        try:
            if package == "eltdx":
                from eltdx._native_abi import load_native
                from qibao_api.gongbu.eltdx_source import _make_client

                abi = load_native().ABI_VERSION
                # Construct and close the same bounded pool used in production.
                # No request or host probing is performed.
                client = _make_client()
                try:
                    report[package] = {"status": "ready", "version": version(package), "native_abi": abi}
                    if online:
                        started = perf_counter()
                        series = client.bars.get("sh600000", period="day", count=3, adjust="none")
                        if not series.bars:
                            raise ValueError("empty daily response")
                        report[package].update(rows=len(series.bars), seconds=round(perf_counter() - started, 3))
                finally:
                    client.close()
            else:
                from qibao_api.gongbu.axdata_quotes import _make_adapter

                adapter = _make_adapter()
                if not adapter.supports("tencent_realtime_snapshot"):
                    raise RuntimeError("Tencent adapter unavailable")
                report[package] = {"status": "ready", "version": version(package), "adapter": "tencent"}
                if online:
                    started = perf_counter()
                    rows = adapter.request("tencent_realtime_snapshot", {"code": ["600000.SH"]})
                    if not rows:
                        raise ValueError("empty quote response")
                    report[package].update(rows=len(rows), seconds=round(perf_counter() - started, 3))
        except Exception as error:
            report[package] = {"status": "error", "error": f"{type(error).__name__}: {error}"}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(item["status"] == "ready" for item in report.values()) else 1
