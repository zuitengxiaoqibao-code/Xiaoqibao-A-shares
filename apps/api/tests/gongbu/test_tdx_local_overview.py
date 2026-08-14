from datetime import datetime, timezone
from decimal import Decimal
from threading import Event

from qibao_api.gongbu.tdx_local_overview import (
    LocalTdxOverviewSource,
    TdxRealtimeQuote,
    build_market_statistics,
    parse_tdx_snapshot,
    probe_tdx_capabilities,
)
import qibao_api.gongbu.tdx_local_overview as tdx_local_overview


NOW = datetime(2026, 7, 29, 3, 30, tzinfo=timezone.utc)


def quote(
    symbol: str,
    name: str,
    *,
    previous_close: str,
    price: str,
    high: str,
    amount_wan: str,
) -> TdxRealtimeQuote:
    return TdxRealtimeQuote(
        symbol=symbol,
        exchange_code=f"{symbol}.{'SH' if symbol.startswith('6') else 'SZ'}",
        name=name,
        previous_close=Decimal(previous_close),
        price=Decimal(price),
        high=Decimal(high),
        low=Decimal(price),
        open=Decimal(previous_close),
        volume=Decimal("100"),
        amount_wan=Decimal(amount_wan),
    )


def test_parse_tdx_snapshot_uses_real_amount_and_prices() -> None:
    result = parse_tdx_snapshot(
        "600000.SH",
        "浦发银行",
        {
            "ErrorId": "0",
            "LastClose": "9.19",
            "Now": "9.33",
            "Max": "9.34",
            "Min": "9.17",
            "Open": "9.19",
            "Volume": "655951",
            "Amount": "60919.41",
        },
    )

    assert result is not None
    assert result.symbol == "600000"
    assert result.price == Decimal("9.33")
    assert result.amount_wan == Decimal("60919.41")


def test_parse_tdx_snapshot_accepts_only_explicit_market_cap_yi() -> None:
    result = parse_tdx_snapshot(
        "600000.SH",
        "浦发银行",
        {
            "ErrorId": "0",
            "LastClose": "9.19",
            "Now": "9.33",
            "Max": "9.34",
            "Min": "9.17",
            "Open": "9.19",
            "Volume": "655951",
            "Amount": "60919.41",
            "MarketCapYi": "2734.50",
            "MarketValue": "273450000000",
        },
    )

    assert result is not None
    assert result.market_cap_yi == Decimal("2734.50")

    without_explicit_unit = parse_tdx_snapshot(
        "600000.SH",
        "浦发银行",
        {
            "ErrorId": "0", "LastClose": "9.19", "Now": "9.33",
            "Max": "9.34", "Min": "9.17", "Open": "9.19",
            "Volume": "655951", "Amount": "60919.41",
            "MarketValue": "273450000000",
        },
    )
    assert without_explicit_unit is not None
    assert without_explicit_unit.market_cap_yi is None


def test_market_statistics_cover_breadth_turnover_and_limit_ecology() -> None:
    quotes = (
        quote("600001", "主板涨停", previous_close="10", price="11", high="11", amount_wan="10000"),
        quote("600002", "主板炸板", previous_close="10", price="10.50", high="11", amount_wan="20000"),
        quote("300001", "创业板跌停", previous_close="10", price="8", high="10", amount_wan="30000"),
        quote("000001", "平盘股票", previous_close="10", price="10", high="10", amount_wan="40000"),
    )

    statistics = build_market_statistics(quotes, observed_at=NOW)

    assert statistics.breadth.rising_count == 2
    assert statistics.breadth.falling_count == 1
    assert statistics.breadth.flat_count == 1
    assert statistics.limit_ecology.limit_up_count == 1
    assert statistics.limit_ecology.limit_down_count == 1
    assert statistics.limit_ecology.broken_limit_up_count == 1
    assert statistics.limit_ecology.seal_rate_percent == Decimal("50.00")
    assert statistics.liquidity.total_amount_yi == Decimal("10")
    assert {item.symbol: item.state for item in statistics.market_stocks} == {
        "600001": "limit_up",
        "600002": "broken_limit_up",
        "300001": "limit_down",
        "000001": "active",
    }
    assert statistics.market_stocks[0].source == "tdx-local-rpc"
    assert statistics.regime_metrics.up_ratio == Decimal("50.00")
    assert statistics.regime_metrics.zt_ratio == Decimal("25.00")
    assert statistics.regime_metrics.dt_ratio == Decimal("25.00")
    assert statistics.regime_metrics.net_positive_ratio is None
    assert statistics.regime_metrics.factor_coverage_percent == Decimal("81.82")


def test_market_statistics_compute_close_position_panic_amplitude_and_failed_limit() -> None:
    quotes = (
        TdxRealtimeQuote(
            symbol="600001", exchange_code="600001.SH", name="触板弱收",
            previous_close=Decimal("10"), price=Decimal("10.50"), high=Decimal("11"),
            low=Decimal("9.80"), open=Decimal("10.20"), volume=Decimal("100"),
            amount_wan=Decimal("10000"),
        ),
        TdxRealtimeQuote(
            symbol="600002", exchange_code="600002.SH", name="恐慌修复",
            previous_close=Decimal("10"), price=Decimal("9.80"), high=Decimal("10.20"),
            low=Decimal("9.00"), open=Decimal("9.20"), volume=Decimal("100"),
            amount_wan=Decimal("20000"),
        ),
    )

    statistics = build_market_statistics(quotes, observed_at=NOW)

    assert statistics.regime_metrics.strong_close_ratio == Decimal("0.00")
    assert statistics.regime_metrics.weak_close_ratio == Decimal("0.00")
    assert statistics.regime_metrics.limit_fail_ratio == Decimal("100.00")
    assert statistics.regime_metrics.panic_ratio == Decimal("50.00")
    assert statistics.regime_metrics.amp_ratio == Decimal("100.00")


def test_st_stocks_use_five_percent_limit_rule() -> None:
    statistics = build_market_statistics((
        quote("600003", "*ST测试", previous_close="10", price="10.50", high="10.50", amount_wan="100"),
    ), observed_at=NOW)

    assert statistics.limit_ecology.limit_up_count == 1


def test_growth_board_stocks_keep_twenty_percent_limit_after_st_warning() -> None:
    statistics = build_market_statistics((
        quote("300003", "ST成长", previous_close="10", price="11", high="11", amount_wan="100"),
    ), observed_at=NOW)

    assert statistics.limit_ecology.limit_up_count == 0
    assert statistics.limit_ecology.broken_limit_up_count == 0


def test_local_overview_uses_self_contained_fallback_when_rpc_is_absent(
    tmp_path,
) -> None:
    expected = build_market_statistics(
        (
            quote(
                "600000", "浦发银行", previous_close="9.19", price="9.28",
                high="9.35", amount_wan="102935.42",
            ),
        ),
        observed_at=NOW,
        source="tencent-realtime+tdx-catalog",
    )

    class MissingRpc:
        def available(self) -> bool:
            return False

        def close(self) -> None:
            return None

    class Fallback:
        def fetch(self):
            return expected

    source = LocalTdxOverviewSource(
        cache_path=tmp_path / "overview.json",
        rpc=MissingRpc(),
        fallback=Fallback(),
        clock=lambda: NOW,
    )

    actual = source.refresh()

    assert actual == expected
    assert source.current() == expected


def test_local_overview_does_not_create_an_rpc_client_when_disabled(
    tmp_path, monkeypatch
) -> None:
    expected = build_market_statistics(
        (quote(
            "600000",
            "浦发银行",
            previous_close="9.19",
            price="9.28",
            high="9.35",
            amount_wan="102935.42",
        ),),
        observed_at=NOW,
        source="fallback",
    )

    class Fallback:
        def fetch(self):
            return expected

    monkeypatch.setattr(
        "qibao_api.gongbu.tdx_local_overview.TdxJsonRpcClient",
        lambda: (_ for _ in ()).throw(AssertionError("unexpected rpc client")),
    )

    source = LocalTdxOverviewSource(
        cache_path=tmp_path / "overview.json",
        rpc=None,
        fallback=Fallback(),
    )

    assert source.refresh() == expected
    source.close()


def test_local_overview_refresh_loop_honors_startup_delay(tmp_path) -> None:
    source = LocalTdxOverviewSource(
        cache_path=tmp_path / "overview.json",
        rpc=None,
        fallback=None,
        initial_delay_seconds=2.0,
    )
    waits: list[float] = []

    def wait(seconds: float) -> bool:
        waits.append(seconds)
        source._stop.set()
        return True

    source._stop = Event()
    source._stop.wait = wait  # type: ignore[method-assign]

    source._refresh_loop()

    assert waits == [2.0]


def test_local_overview_refresh_failures_are_rate_limited(tmp_path, monkeypatch) -> None:
    source = LocalTdxOverviewSource(
        cache_path=tmp_path / "overview.json",
        rpc=None,
        fallback=None,
    )
    warnings: list[tuple[object, ...]] = []
    recoveries: list[tuple[object, ...]] = []
    monkeypatch.setattr(tdx_local_overview.logger, "warning", lambda *args, **kwargs: warnings.append(args))
    monkeypatch.setattr(tdx_local_overview.logger, "info", lambda *args, **kwargs: recoveries.append(args))

    error = OSError("bridge unavailable")
    for _ in range(21):
        source._record_refresh_failure(error)

    assert len(warnings) == 2
    assert "error_type=%s" in str(warnings[0][0])
    source._record_refresh_success()
    assert len(recoveries) == 1


def test_probe_tdx_capabilities_reports_real_read_only_methods_and_partial_support() -> None:
    class FakeRpc:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def available(self) -> bool:
            return True

        def call(self, method: str, params: dict) -> object:
            self.calls.append(method)
            if method == "get_stock_list":
                return {"ErrorId": "0", "Value": [{"Code": "600000.SH", "Name": "浦发银行"}]}
            if method == "get_market_snapshot":
                return {"ErrorId": "0", "Now": "9.28"}
            if method == "get_sector_list":
                return {"ErrorId": "0", "Value": [{"Code": "BK0001", "Name": "测试板块"}]}
            raise OSError("unsupported method")

    rpc = FakeRpc()
    result = probe_tdx_capabilities(rpc, stock_code="600000.SH")

    assert result["status"] == "partial"
    assert result["reachable"] is True
    assert {item["key"] for item in result["capabilities"]} >= {
        "catalog", "snapshot", "sectors", "more_info", "stock_info", "formula",
    }
    assert {item["key"] for item in result["capabilities"] if item["status"] == "ready"} == {
        "catalog", "snapshot", "sectors",
    }
    assert "get_more_info" in rpc.calls


def test_probe_tdx_capabilities_uses_table_list_for_professional_methods() -> None:
    class ProfessionalRpc:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        def available(self) -> bool:
            return True

        def call(self, method: str, params: dict) -> object:
            self.calls.append((method, params))
            if method == "get_stock_list":
                return {"ErrorId": "0", "Value": [{"Code": "600000.SH", "Name": "浦发银行"}]}
            if method == "get_market_snapshot":
                return {"ErrorId": "0", "Now": "9.28"}
            if method == "get_sector_list":
                return {"ErrorId": "0", "Value": [{"Code": "BK0001", "Name": "测试板块"}]}
            if method == "get_financial_data":
                return {"ErrorId": "0", "Value": [{"Code": "600000.SH", "Fn193": "12.5"}]}
            return {"ErrorId": "12", "Value": []}

    rpc = ProfessionalRpc()
    result = probe_tdx_capabilities(rpc, stock_code="600000.SH")

    financial_call = next(call for call in rpc.calls if call[0] == "get_financial_data")
    assert financial_call[1]["table_list"] == ["Fn193"]
    assert "field_list" not in financial_call[1]
    financial_capability = next(item for item in result["capabilities"] if item["key"] == "professional_finance")
    assert financial_capability["status"] == "ready"
    assert financial_capability["semantic_status"] == "detected_only"
    assert "字段语义和单位尚未映射" in financial_capability["detail"]


def test_probe_tdx_capabilities_rejects_unwrapped_professional_rows_without_error_contract() -> None:
    class ListRpc:
        def available(self) -> bool:
            return True

        def call(self, method: str, params: dict) -> object:
            if method == "get_financial_data":
                return [{"Code": "600000.SH", "Fn193": "12.5"}]
            return {"ErrorId": "12", "Value": []}

    result = probe_tdx_capabilities(ListRpc(), stock_code="600000.SH")
    status = next(item["status"] for item in result["capabilities"] if item["key"] == "professional_finance")
    assert status == "unavailable"


def test_probe_tdx_capabilities_marks_everything_unavailable_when_bridge_is_down() -> None:
    class MissingRpc:
        def available(self) -> bool:
            return False

        def call(self, method: str, params: dict) -> object:
            raise AssertionError("unreachable bridge must not receive probes")

    result = probe_tdx_capabilities(MissingRpc())

    assert result["status"] == "unavailable"
    assert result["reachable"] is False
    assert all(item["status"] == "unavailable" for item in result["capabilities"])


def test_probe_tdx_capabilities_does_not_treat_empty_or_error_payloads_as_ready() -> None:
    class EmptyRpc:
        def available(self) -> bool:
            return True

        def call(self, method: str, params: dict) -> object:
            if method == "get_stock_list":
                return {"ErrorId": "0", "Value": []}
            if method == "get_sector_list":
                return {"ErrorId": "12", "Value": []}
            return None

    result = probe_tdx_capabilities(EmptyRpc())

    statuses = {item["key"]: item["status"] for item in result["capabilities"]}
    assert statuses["catalog"] == "unavailable"
    assert statuses["sectors"] == "unavailable"
    assert statuses["snapshot"] == "unavailable"
    assert result["status"] == "unavailable"


def test_probe_tdx_capabilities_does_not_treat_nested_professional_records_as_ready() -> None:
    class NestedProfessionalRpc:
        def available(self) -> bool:
            return True

        def call(self, method: str, params: dict) -> object:
            if method == "get_bkjy_value":
                return {
                    "ErrorId": "0",
                    "Value": {
                        "880660.SH": {
                            "BK9": [
                                {"Date": "20260807", "Value": ["0.00", "0.00"]}
                            ]
                        }
                    },
                }
            return {"ErrorId": "12", "Value": []}

    result = probe_tdx_capabilities(NestedProfessionalRpc())
    status = next(
        item["status"]
        for item in result["capabilities"]
        if item["key"] == "professional_sector_trade"
    )
    assert status == "unavailable"
