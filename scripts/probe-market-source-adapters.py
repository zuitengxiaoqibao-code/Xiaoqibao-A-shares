"""Read-only network probe: never writes quotes into a user database."""
import json
from time import perf_counter

from qibao_api.gongbu.axdata_quotes import AxDataTencentQuoteSource
from qibao_api.gongbu.eltdx_source import EltdxSource


def probe():
    source = EltdxSource()
    try:
        for symbol in ("600000", "000001", "301666", "920000"):
            started = perf_counter()
            try:
                bars = source.fetch_daily(symbol, 3)
                print(json.dumps({"source": "eltdx", "symbol": symbol, "seconds": round(perf_counter() - started, 3),
                    "rows": [bar.model_dump(mode="json") for bar in bars]}, ensure_ascii=False), flush=True)
            except Exception as error:
                print(json.dumps({"source": "eltdx", "symbol": symbol, "seconds": round(perf_counter() - started, 3),
                    "error": f"{type(error).__name__}: {error}"}, ensure_ascii=False), flush=True)
        try:
            values, warnings = source.fetch_indices()
            print(json.dumps({"source": "eltdx", "indices": [q.model_dump(mode="json") for q in values],
                "warnings": warnings}, ensure_ascii=False), flush=True)
            values, warnings = source.fetch_minutes("sh000001")
            print(json.dumps({"source": "eltdx", "minutes": len(values), "last": values[-1].model_dump(mode="json") if values else None,
                "warnings": warnings}, ensure_ascii=False), flush=True)
        except Exception as error:
            print("eltdx minutes:", type(error).__name__, str(error), flush=True)
        axdata = AxDataTencentQuoteSource()
        try:
            values, warnings = axdata.fetch_stocks(("600000", "000001", "920000"))
            print(json.dumps({"source": "axdata-tencent", "quotes": [q.model_dump(mode="json") for q in values], "warnings": warnings}, ensure_ascii=False), flush=True)
        except Exception as error:
            print("axdata:", type(error).__name__, str(error), flush=True)
    finally:
        source.close()


if __name__ == "__main__":
    probe()
