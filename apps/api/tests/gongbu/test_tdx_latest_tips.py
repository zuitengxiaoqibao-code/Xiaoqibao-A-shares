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
    assert items[0].title == "签署战略合作协议"
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


def test_parse_latest_tips_filters_f10_navigation_and_financial_table_noise() -> None:
    text = (
        "☆603123 翼微股份 更新日期：☆ 通达信沪深京F10 ★本栏包括【1.最新提示】【2.互动问答】"
        "【3.最新公告】【4.最新报道】【5.最新异动】【6.大宗交易】【7.融资融券】 | "
        "●最新主要指标 | 2025-12-31 | 2025-09-30 | 每股收益（元） -0.0400 | 每股净资产（元） 2.0394 | "
        "●最新公告：2026-08-01 翼微股份（603123）关于非公开发行公司债券获得上交所挂牌转让无异议的公告 | "
        "●最新报道：2026-07-22 翼微股份获得重大客户订单 | "
        "●业绩预告：2026-07-15 预计上半年净利润 8000 万元至 6500 万元，预计与上年同期相比变动幅度为 8.87%-18.72%"
    )

    items = parse_latest_tips(text, source="mootdx-f10", observed_at=OBSERVED_AT)

    assert len(items) == 3
    assert all("每股收益" not in item.raw_text for item in items)
    assert all("本栏包括" not in item.raw_text for item in items)
    performance = next(item for item in items if item.category == "业绩预告")
    assert performance.title == "净利润预计同比下降 8.87%～18.72%"
    assert "8000 万元至 6500 万元" in performance.summary
    announcement = next(item for item in items if item.category == "公告与合同")
    assert "债券" in announcement.title


def test_parse_latest_tips_extracts_financial_fields_without_table_or_navigation_noise() -> None:
    text = """
☆603009 北特科技 更新日期：☆ 通达信沪深京F10
★本栏包括【1.最新提示】【2.互动问答】【3.最新公告】【4.最新报道】
| 2026-03-31 | 营业收入(万元):58571.50 | 同比增长(%):8.04 |
| 净利润(万元):2717.81 | 同比增长(%):17.86 |
最新分红扩股： | |
●2026-07-20 北特科技：关于向特定对象发行限售股上市流通的公告
"""

    items = parse_latest_tips(text, source="mootdx-f10", observed_at=OBSERVED_AT)

    assert len(items) == 2
    financial = next(item for item in items if item.category == "业绩预告")
    assert financial.title == "季度经营数据同比增长"
    assert "营业收入 58571.50 万元，同比增长 8.04%" in financial.summary
    assert "净利润 2717.81 万元，同比增长 17.86%" in financial.summary
    assert financial.tone == "positive"
    assert "下降" not in financial.title
    unlock = next(item for item in items if item.category == "资金与融资")
    assert unlock.title == "限售股解禁事项"
    assert all("本栏包括" not in item.raw_text for item in items)
    assert all("通达信沪深京F10" not in item.raw_text for item in items)
    assert all("|" not in item.raw_text for item in items)
    assert all("最新分红扩股" not in item.raw_text for item in items)
