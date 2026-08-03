import json
from datetime import date, datetime, timezone
import pytest

from qibao_api.convertible_bonds.adapters import (
    EastmoneyBondUniverseSource,
    RawHttpResponse,
    parse_eastmoney_bond_universe,
)
from qibao_api.convertible_bonds.models import BondUniverseSnapshot
from qibao_api.convertible_bonds.universe_repository import BondUniverseRepository


def universe_payload() -> bytes:
    return json.dumps(
        {
            "result": {
                "pages": 1,
                "data": [
                    {
                        "SECURITY_CODE": "113065",
                        "SECURITY_NAME_ABBR": "测试转债",
                        "CONVERT_STOCK_CODE": "600001",
                        "LISTING_DATE": "2023-03-10 00:00:00",
                        "EXPIRE_DATE": "2028-09-15 00:00:00",
                        "DELIST_DATE": None,
                        "CEASE_DATE": None,
                    },
                    {
                        "SECURITY_CODE": "110002",
                        "SECURITY_NAME_ABBR": "历史转债",
                        "CONVERT_STOCK_CODE": "600219",
                        "LISTING_DATE": "2008-05-13 00:00:00",
                        "EXPIRE_DATE": "2009-09-18 00:00:00",
                        "DELIST_DATE": "2009-09-24 00:00:00",
                        "CEASE_DATE": "2009-09-17 00:00:00",
                    },
                    {
                        "SECURITY_CODE": "999999",
                        "SECURITY_NAME_ABBR": "不是转债",
                        "CONVERT_STOCK_CODE": "600001",
                        "LISTING_DATE": "2023-03-10 00:00:00",
                        "EXPIRE_DATE": "2028-09-15 00:00:00",
                    },
                ],
            }
        },
        ensure_ascii=False,
    ).encode("utf-8")


def test_parse_eastmoney_bond_universe_filters_delisted_and_invalid_codes() -> None:
    snapshot = parse_eastmoney_bond_universe(
        universe_payload(), observed_at=datetime(2026, 7, 17, tzinfo=timezone.utc)
    )

    assert [item.bond_code for item in snapshot.items] == ["113065"]
    assert snapshot.items[0].linked_stock_code == "600001"
    assert snapshot.items[0].maturity == date(2028, 9, 15)
    assert snapshot.items[0].status == "active"
    assert snapshot.raw_identity

    with pytest.raises(ValueError, match="incomplete"):
        parse_eastmoney_bond_universe(b'{"result": null}', observed_at=datetime(2026, 7, 17, tzinfo=timezone.utc))


@pytest.mark.asyncio
async def test_universe_source_requests_all_rows_and_rejects_bad_status() -> None:
    seen: list[dict[str, str]] = []

    async def transport(url: str, params: dict[str, str]) -> RawHttpResponse:
        seen.append(params)
        return RawHttpResponse(200, universe_payload())

    source = EastmoneyBondUniverseSource(transport=transport, clock=lambda: datetime(2026, 7, 17, tzinfo=timezone.utc))
    snapshot = await source.fetch()

    assert snapshot.source == "eastmoney"
    assert seen[0]["reportName"] == "RPT_BOND_CB_LIST"
    assert seen[0]["pageNumber"] == "1"
    assert snapshot.items[0].name == "测试转债"

    async def unavailable(_: str, __: dict[str, str]) -> RawHttpResponse:
        return RawHttpResponse(503, b"unavailable")

    with pytest.raises(ValueError, match="status 503"):
        await EastmoneyBondUniverseSource(transport=unavailable).fetch()


def test_universe_repository_keeps_latest_snapshot_and_rejects_mutation(tmp_path) -> None:
    repository = BondUniverseRepository(tmp_path / "bond-universe.sqlite3")
    snapshot = BondUniverseSnapshot.model_validate(
        parse_eastmoney_bond_universe(
            universe_payload(), observed_at=datetime(2026, 7, 17, tzinfo=timezone.utc)
        ).model_dump(mode="json")
    )
    first_id = repository.append(snapshot)
    latest = repository.latest()

    assert first_id
    assert latest is not None
    assert [item.bond_code for item in latest.items] == ["113065"]

    with pytest.raises(Exception):
        repository.connection.execute("UPDATE bond_universe_snapshots SET source='tampered'")
    repository.close()


def test_service_dashboard_reports_discovered_and_diagnosed_counts(tmp_path) -> None:
    from qibao_api.convertible_bonds.service import ConvertibleBondService

    universe = BondUniverseRepository(tmp_path / "bond-universe.sqlite3")
    universe.append(
        parse_eastmoney_bond_universe(
            universe_payload(), observed_at=datetime(2026, 7, 17, tzinfo=timezone.utc)
        )
    )

    class ClauseRepository:
        def all_latest(self):
            return []

    class DiagnosisRepository:
        def latest_by_bond(self):
            return [{"bond_code": "113065", "payload": {}}]

    service = ConvertibleBondService(
        None,
        None,
        None,
        ClauseRepository(),
        None,
        DiagnosisRepository(),
        universe_repository=universe,
    )

    dashboard = service.dashboard()
    assert dashboard["discovered_count"] == 1
    assert dashboard["diagnosed_count"] == 1
    assert dashboard["bond_codes"] == ["113065"]
    assert dashboard["diagnosed_outside_universe_count"] == 0
    universe.close()


def test_service_does_not_rank_diagnosis_outside_current_universe(tmp_path) -> None:
    from qibao_api.convertible_bonds.service import ConvertibleBondService

    universe = BondUniverseRepository(tmp_path / "bond-universe.sqlite3")
    universe.append(
        parse_eastmoney_bond_universe(
            universe_payload(), observed_at=datetime(2026, 7, 17, tzinfo=timezone.utc)
        )
    )

    class ClauseRepository:
        def all_latest(self):
            return []

    class DiagnosisRepository:
        def latest_by_bond(self):
            return [{"bond_code": "110002", "payload": {"status": "ready"}}]

    service = ConvertibleBondService(
        None,
        None,
        None,
        ClauseRepository(),
        None,
        DiagnosisRepository(),
        universe_repository=universe,
    )

    assert service.candidates()["items"] == []
    assert service.candidates()["coverage"]["diagnosed_count"] == 0
    universe.close()


def test_diagnosis_state_explains_four_observation_states() -> None:
    from qibao_api.convertible_bonds.service import classify_diagnosis_state

    assert classify_diagnosis_state(None) == ("discovered", "尚未诊断，行情、条款与估值尚未核验")
    assert classify_diagnosis_state({"status": "stale_quote"}) == (
        "unavailable", "行情已过期，未进入观察候选"
    )
    assert classify_diagnosis_state({
        "status": "ready", "bond": {"suspended": False, "price": "110"},
        "risk": {"outcome": "exclude"},
    }) == ("risk_excluded", "规则风险拦截")
    assert classify_diagnosis_state({
        "status": "ready", "bond": {"suspended": False, "price": "110"},
        "risk": {"outcome": "eligible"},
    }) == ("diagnosed", None)


@pytest.mark.asyncio
async def test_service_diagnoses_first_discovered_bonds_and_reports_per_bond_failures(tmp_path) -> None:
    from qibao_api.convertible_bonds.service import ConvertibleBondService

    universe = BondUniverseRepository(tmp_path / "bond-universe.sqlite3")
    snapshot = parse_eastmoney_bond_universe(
        universe_payload(), observed_at=datetime(2026, 7, 17, tzinfo=timezone.utc)
    )
    second = snapshot.items[0].model_copy(update={"bond_code": "123064", "name": "second"})
    universe.append(snapshot.model_copy(update={"items": snapshot.items + (second,)}))

    class ClauseRepository:
        def all_latest(self):
            return []

    class DiagnosisRepository:
        def latest_by_bond(self):
            return []

    service = ConvertibleBondService(
        None,
        None,
        None,
        ClauseRepository(),
        None,
        DiagnosisRepository(),
        universe_repository=universe,
    )
    calls: list[str] = []

    async def diagnose(code: str) -> dict:
        calls.append(code)
        if code == "123064":
            raise ValueError("provider field invalid")
        return {"status": "ready", "risk": {"outcome": "exclude"}}

    service.diagnose = diagnose

    report = await service.diagnose_discovered(limit=2)

    assert calls == ["113065", "123064"]
    assert report["requested"] == 2
    assert report["diagnosed_count"] == 1
    assert report["unavailable_count"] == 1
    assert report["items"] == [
        {"bond_code": "113065", "state": "diagnosed", "status": "ready", "risk_outcome": "exclude"},
        {"bond_code": "123064", "state": "unavailable", "reason_code": "invalid_provider_data"},
    ]
    universe.close()
