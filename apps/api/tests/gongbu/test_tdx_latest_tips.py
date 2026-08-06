from datetime import datetime, timezone

from qibao_api.gongbu.tdx_latest_tips import parse_latest_tips


OBSERVED_AT = datetime(2026, 8, 6, 8, tzinfo=timezone.utc)


def test_parse_latest_tips_extracts_categories_dates_tones_and_raw_evidence() -> None:
    text = (
        "●最新公告：2026-08-05 16:42 公司与某客户签署战略合作协议，金额 2.1 亿元 | "
        "●业绩预告：2026-07-15 预计上半年净利润同比下降 30%-40% | "
        "●风险提示：2026-07-10 公司股票存在交易风险"
    )

    items = parse_latest_tips(text, source="mootdx-f10", observed_at=OBSERVED_AT)

    assert len(items) == 3
    assert items[0].category == "公告与合同"
    assert items[0].date == "2026-08-05"
    assert items[0].tone == "positive"
    assert "战略合作协议" in items[0].summary
    assert items[0].raw_text.startswith("●最新公告")
    assert items[1].category == "业绩预告"
    assert items[1].tone == "risk"
    assert items[2].category == "风险提醒"
    assert items[2].tone == "risk"
    assert all(item.id and item.source == "mootdx-f10" for item in items)


def test_parse_latest_tips_keeps_unclassified_fragment_as_raw_evidence() -> None:
    items = parse_latest_tips(
        "2026-08-01 公司完成普通工商变更登记，具体内容见原文",
        source="mootdx-f10",
        observed_at=OBSERVED_AT,
    )

    assert len(items) == 1
    assert items[0].category == "其他"
    assert items[0].title == "原文待整理"
    assert items[0].tone == "unknown"
    assert "工商变更登记" in items[0].summary
    assert items[0].raw_text != items[0].summary


def test_parse_latest_tips_returns_empty_tuple_for_missing_text() -> None:
    assert parse_latest_tips(None, source="mootdx-f10", observed_at=OBSERVED_AT) == ()
    assert parse_latest_tips("   ", source="mootdx-f10", observed_at=OBSERVED_AT) == ()
