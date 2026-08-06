from datetime import datetime, timezone

import pytest

from qibao_api.gongbu.tdx_local_calendar import (
    TdxCalendarDataUnavailable,
    TdxLocalIpoSource,
    parse_tdx_ipo_info,
)


NOW = datetime(2026, 8, 6, 8, 0, tzinfo=timezone.utc)


def test_parse_tdx_ipo_info_accepts_explicit_stock_and_bond_events() -> None:
    result = parse_tdx_ipo_info(
        {
            "ErrorId": "0",
            "Value": [
                {
                    "Code": "732001.SH",
                    "Name": "测试新股",
                    "Type": "新股",
                    "ApplyDate": "2026-08-07",
                    "ListingDate": "2026-08-17",
                },
                {
                    "Code": "123001.SZ",
                    "Name": "测试转债",
                    "Type": "新债",
                    "ApplyDate": "2026/08/08",
                    "ListingDate": "2026/08/20",
                },
            ],
        },
        fetched_at=NOW,
    )

    assert [item.code for item in result] == ["732001", "123001"]
    assert result[0].kind == "新股"
    assert result[0].subscription_date.isoformat() == "2026-08-07"
    assert result[1].kind == "新债"
    assert result[1].listing_date.isoformat() == "2026-08-20"
    assert result[0].source == "tdx-local-rpc"


def test_parse_tdx_ipo_info_rejects_empty_or_incomplete_rows() -> None:
    with pytest.raises(TdxCalendarDataUnavailable):
        parse_tdx_ipo_info({"ErrorId": "0", "Value": []}, fetched_at=NOW)

    with pytest.raises(TdxCalendarDataUnavailable):
        parse_tdx_ipo_info(
            {"ErrorId": "0", "Value": [{"Code": "732001.SH", "Name": "缺日期"}]},
            fetched_at=NOW,
        )


def test_parse_tdx_ipo_info_rejects_error_payload_without_fallback_values() -> None:
    with pytest.raises(TdxCalendarDataUnavailable):
        parse_tdx_ipo_info({"ErrorId": "12", "Value": []}, fetched_at=NOW)


def test_local_ipo_source_calls_only_read_only_calendar_method() -> None:
    class Rpc:
        def __init__(self) -> None:
            self.calls = []

        def available(self) -> bool:
            return True

        def call(self, method, params):
            self.calls.append((method, params))
            return {
                "ErrorId": "0",
                "Value": [{
                    "Code": "732001.SH", "Name": "测试新股", "Type": "新股",
                    "ApplyDate": "2026-08-07",
                }],
            }

        def close(self) -> None:
            return None

    rpc = Rpc()
    source = TdxLocalIpoSource(lambda: rpc, clock=lambda: NOW)
    result = source.fetch()

    assert result[0].code == "732001"
    assert rpc.calls == [("get_ipo_info", {"market": "5"})]
