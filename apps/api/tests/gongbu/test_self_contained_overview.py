from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from qibao_api.gongbu.self_contained_overview import (
    SelfContainedOverviewProvider,
    MootdxAShareCatalogSource,
    parse_tencent_realtime_quotes,
)


NOW = datetime(2026, 7, 29, 8, 15, tzinfo=timezone.utc)


def quote_line(
    instrument: str,
    name: str,
    symbol: str,
    *,
    price: str,
    previous_close: str,
    high: str,
    low: str,
    opening: str,
    volume: str,
    amount_wan: str,
) -> str:
    fields = [""] * 53
    fields[1] = name
    fields[2] = symbol
    fields[3] = price
    fields[4] = previous_close
    fields[5] = opening
    fields[6] = volume
    fields[30] = "20260729161433"
    fields[33] = high
    fields[34] = low
    fields[37] = amount_wan
    return f'v_{instrument}="{"~".join(fields)}";'


class Response:
    status_code = 200

    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


class Client:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.urls: list[str] = []

    def get(self, url: str) -> Response:
        self.urls.append(url)
        return Response(self.payload)


def test_tencent_realtime_parser_preserves_verified_price_fields() -> None:
    raw = quote_line(
        "sh600000",
        "浦发银行",
        "600000",
        price="9.28",
        previous_close="9.19",
        high="9.35",
        low="9.17",
        opening="9.19",
        volume="1109627",
        amount_wan="102935.42",
    ).encode("gbk")

    quotes = parse_tencent_realtime_quotes(raw, {"600000": "浦发银行"})

    assert len(quotes) == 1
    assert quotes[0].price == Decimal("9.28")
    assert quotes[0].previous_close == Decimal("9.19")
    assert quotes[0].amount_wan == Decimal("102935.42")
    assert quotes[0].exchange_code == "600000.SH"


def test_provider_builds_market_snapshot_without_external_json_rpc() -> None:
    payload = "\n".join((
        quote_line(
            "sh600000", "浦发银行", "600000", price="9.28",
            previous_close="9.19", high="9.35", low="9.17", opening="9.19",
            volume="1109627", amount_wan="102935.42",
        ),
        quote_line(
            "sz000001", "平安银行", "000001", price="12.00",
            previous_close="12.10", high="12.15", low="11.95", opening="12.08",
            volume="200000", amount_wan="24000.00",
        ),
    )).encode("gbk")
    client = Client(payload)
    provider = SelfContainedOverviewProvider(
        catalog_loader=lambda: (("600000", "浦发银行"), ("000001", "平安银行")),
        client=client,
        clock=lambda: NOW,
        batch_size=80,
        max_workers=1,
    )

    snapshot = provider.fetch()

    assert snapshot.source == "tencent-realtime+tdx-catalog"
    assert snapshot.quote_count == 2
    assert snapshot.universe_count == 2
    assert snapshot.breadth.rising_count == 1
    assert snapshot.breadth.falling_count == 1
    assert snapshot.quality == "ready"
    assert client.urls == ["https://qt.gtimg.cn/q=sh600000,sz000001"]


def test_catalog_fallback_intersects_directory_with_local_tdx_daily_files(
    tmp_path,
) -> None:
    for exchange, symbol in (("sh", "600000"), ("sz", "000001")):
        folder = tmp_path / exchange / "lday"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{exchange}{symbol}.day").write_bytes(b"verified-local-day")
    instruments = {
        "600000": SimpleNamespace(symbol="600000", name="浦发银行", exchange="sh"),
        "000001": SimpleNamespace(symbol="000001", name="平安银行", exchange="sz"),
        "600001": SimpleNamespace(symbol="600001", name="目录旧记录", exchange="sh"),
        "920001": SimpleNamespace(symbol="920001", name="北交股票", exchange="bj"),
    }

    class Directory:
        def active_symbols(self):
            return tuple(instruments)

        def resolve(self, symbol):
            return instruments[symbol]

    remote_calls = []
    source = MootdxAShareCatalogSource(
        directory=Directory(),
        vipdoc_root=tmp_path,
        servers=(("127.0.0.1", 1),),
        minimum_count=2,
        client_factory=lambda **kwargs: remote_calls.append(kwargs),
    )

    assert source.load() == (("000001", "平安银行"), ("600000", "浦发银行"))
    assert source.last_source == "local-tdx-vipdoc-catalog"
    assert remote_calls == []
