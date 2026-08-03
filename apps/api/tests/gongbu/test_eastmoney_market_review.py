import json
from datetime import date, datetime, timezone
from decimal import Decimal

from qibao_api.gongbu.eastmoney_market_review import (
    parse_dragon_tiger_details,
    parse_dragon_tiger_seats,
)


NOW = datetime(2026, 7, 30, 9, tzinfo=timezone.utc)


def payload(rows: list[dict]) -> bytes:
    return json.dumps({"result": {"data": rows}}, ensure_ascii=False).encode("utf-8")


def test_dragon_tiger_parser_preserves_reported_money_and_reason() -> None:
    rows = parse_dragon_tiger_details(payload([{
        "SECURITY_CODE": "300308",
        "SECURITY_NAME_ABBR": "中际旭创",
        "TRADE_DATE": "2026-07-28 00:00:00",
        "EXPLANATION": "日涨幅偏离值达到7%的前5只证券",
        "BILLBOARD_BUY_AMT": 2839000000,
        "BILLBOARD_SELL_AMT": 1811000000,
        "BILLBOARD_NET_AMT": 1028000000,
        "CHANGE_RATE": 19.99,
    }]), observed_at=NOW)

    assert rows[0].symbol == "300308"
    assert rows[0].trade_date == date(2026, 7, 28)
    assert rows[0].net_amount_yi == Decimal("10.28")
    assert rows[0].reason.startswith("日涨幅偏离值")


def test_dragon_tiger_seat_parser_keeps_buy_and_sell_separately() -> None:
    rows = parse_dragon_tiger_seats(payload([{
        "SECURITY_CODE": "300308",
        "TRADE_DATE": "2026-07-28 00:00:00",
        "OPERATEDEPT_NAME": "深股通专用",
        "BUY": 5925000000,
        "SELL": 4896000000,
        "NET": 1029000000,
    }]), observed_at=NOW)

    assert rows[0].seat_name == "深股通专用"
    assert rows[0].buy_amount_yi == Decimal("59.25")
    assert rows[0].sell_amount_yi == Decimal("48.96")
    assert rows[0].net_amount_yi == Decimal("10.29")
