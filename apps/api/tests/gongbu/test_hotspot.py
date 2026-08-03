import json
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest

from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.risk import ComplianceRecord
from qibao_api.gongbu.hotspot import (
    HotspotIngestionService,
    TonghuashunHotspotSource,
    parse_tonghuashun_hotspots,
)
from qibao_api.gongbu.news_repository import NewsRepository
from qibao_api.libu_compliance.repository import (
    ComplianceRepository,
    SourceAuthorizationError,
)


TRADING_DATE = date(2026, 7, 17)
CHINA_TZ = timezone(timedelta(hours=8))
FETCHED_AT = datetime(2026, 7, 17, 10, 31, tzinfo=CHINA_TZ)


def payload(*rows, error_code=0) -> dict:
    return {
        "errocode": error_code,
        "errormsg": "" if error_code == 0 else "upstream rejected",
        "date": TRADING_DATE.isoformat(),
        "data": list(rows),
    }


def row(
    *, code="000722", name="湖南发展",
    reason="水力发电+中报预增+湖南国资",
) -> dict:
    return {
        "id": 91868684,
        "code": code,
        "name": name,
        "reason": reason,
        "date": TRADING_DATE.isoformat(),
        "market": "sz",
    }


def encoded(value: dict, encoding="utf-8-sig") -> bytes:
    return json.dumps(value, ensure_ascii=False).encode(encoding)


def authorize(compliance: ComplianceRepository) -> None:
    compliance.append_record(ComplianceRecord(
        record_id="authorize-tonghuashun-hotspot",
        asset=AssetKind.A_SHARE,
        source="tonghuashun",
        permission_state="authorized",
        permission_reference="personal research",
        disclaimer_version="2026-07",
        user_acknowledged_at=FETCHED_AT,
        recorded_at=FETCHED_AT,
    ))


def test_parser_accepts_real_utf8_bom_shape_without_invented_quote_fields() -> None:
    observations = parse_tonghuashun_hotspots(
        encoded(payload(row())),
        trading_date=TRADING_DATE,
        fetched_at=FETCHED_AT,
    )

    assert len(observations) == 1
    observation = observations[0]
    assert observation.symbol == "000722"
    assert observation.name == "湖南发展"
    assert observation.themes == ("水力发电", "中报预增", "湖南国资")
    assert observation.observed_at == FETCHED_AT
    assert observation.fetched_at == FETCHED_AT
    assert observation.source == "tonghuashun-hotspot"
    assert set(observation.model_dump()) == {
        "source_record_id", "symbol", "name", "trading_date", "themes",
        "observed_at", "fetched_at", "source", "raw_snapshot",
    }


def test_parser_strictly_falls_back_to_gbk() -> None:
    observations = parse_tonghuashun_hotspots(
        encoded(payload(row()), "gbk"),
        trading_date=TRADING_DATE,
        fetched_at=FETCHED_AT,
    )

    assert observations[0].themes[0] == "水力发电"


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (payload(row(), error_code=10003), "upstream rejected"),
        (payload(row(code="123")), "A-share code"),
        (payload(row(name="")), "name"),
        (payload(row(reason=" + ")), "themes"),
        (payload({**row(), "date": "2026-07-16"}), "trading date"),
        (payload(row(), row()), "duplicate symbol"),
    ],
)
def test_parser_rejects_an_invalid_or_incomplete_batch(value, message) -> None:
    with pytest.raises(ValueError, match=message):
        parse_tonghuashun_hotspots(
            encoded(value), trading_date=TRADING_DATE, fetched_at=FETCHED_AT
        )


def test_source_uses_exact_date_path_and_retries_one_transient_failure() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(503, content=b"temporary")
        return httpx.Response(200, content=encoded(payload(row())))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        observations = TonghuashunHotspotSource(client).fetch(
            TRADING_DATE, fetched_at=FETCHED_AT
        )

    assert observations[0].symbol == "000722"
    assert len(requests) == 2
    assert requests[0].url.path == (
        "/event/api/getharden/date/2026-07-17/"
        "orderby/date/orderway/desc/charset/GBK/"
    )
    assert requests[0].headers["user-agent"].startswith("Mozilla/5.0")


def test_ingestion_requires_independent_authorization_and_is_idempotent(
    tmp_path,
) -> None:
    compliance = ComplianceRepository(tmp_path / "compliance.sqlite3")
    compliance.set_feature_sources(
        "market_hotspots", AssetKind.A_SHARE, ("tonghuashun",)
    )
    repository = NewsRepository(tmp_path / "news.sqlite3")

    class Source:
        def fetch(self, trading_date, *, fetched_at):
            return parse_tonghuashun_hotspots(
                encoded(payload(row())),
                trading_date=trading_date,
                fetched_at=fetched_at,
            )

    service = HotspotIngestionService(Source(), repository, compliance)
    with pytest.raises(SourceAuthorizationError, match="tonghuashun"):
        service.sync(TRADING_DATE, fetched_at=FETCHED_AT)

    authorize(compliance)
    first = service.sync(TRADING_DATE, fetched_at=FETCHED_AT)
    second = service.sync(TRADING_DATE, fetched_at=FETCHED_AT)

    assert first.model_dump() == {
        "fetched": 1, "inserted": 1, "clusters": 1, "events": 1,
    }
    assert second.model_dump() == {
        "fetched": 1, "inserted": 0, "clusters": 1, "events": 0,
    }
    article = repository.articles()[0]
    assert json.loads(article.raw_snapshot)["reason"] == "水力发电+中报预增+湖南国资"
    event = repository.events()[0]
    assert event.event_type == "market_hotspot"
    assert event.affected_instruments == ((AssetKind.A_SHARE, "000722"),)
    assert event.themes == ("水力发电", "中报预增", "湖南国资")
    assert event.review_state == "verified"
    assert event.association_confidence == 1
    repository.close()
    compliance.close()


def test_ingestion_appends_a_new_event_when_source_themes_change(tmp_path) -> None:
    compliance = ComplianceRepository(tmp_path / "compliance.sqlite3")
    compliance.set_feature_sources(
        "market_hotspots", AssetKind.A_SHARE, ("tonghuashun",)
    )
    authorize(compliance)
    repository = NewsRepository(tmp_path / "news.sqlite3")

    class Source:
        reason = "水力发电+湖南国资"

        def fetch(self, trading_date, *, fetched_at):
            return parse_tonghuashun_hotspots(
                encoded(payload(row(reason=self.reason))),
                trading_date=trading_date,
                fetched_at=fetched_at,
            )

    source = Source()
    service = HotspotIngestionService(source, repository, compliance)
    service.sync(TRADING_DATE, fetched_at=FETCHED_AT)
    source.reason = "水力发电+资产重组+湖南国资"
    service.sync(
        TRADING_DATE, fetched_at=FETCHED_AT + timedelta(hours=3)
    )

    events = repository.events()
    assert len(events) == 2
    assert events[0].event_id != events[1].event_id
    assert events[0].themes == ("水力发电", "湖南国资")
    assert events[1].themes == ("水力发电", "资产重组", "湖南国资")
    repository.close()
    compliance.close()
