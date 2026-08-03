from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.contracts.market_overview import (
    OverviewRegimeAssessment,
    OverviewRegimeMetrics,
)
from qibao_api.contracts.quant_strategy import QuantStrategyDashboard
from qibao_api.dependencies import get_quant_strategy_service, get_server_time
from qibao_api.routes.quant_strategy import router


NOW = datetime(2026, 7, 31, 6, 0, tzinfo=timezone.utc)


class Service:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = []

    def current(self, now, *, as_of=None, limit=12):
        self.calls.append((now, as_of, limit))
        if self.fail:
            raise OSError("local market unavailable")
        return QuantStrategyDashboard(
            status="partial",
            as_of=date(2026, 7, 31),
            observed_at=NOW,
            generated_at=NOW,
            market_observed_at=NOW,
            data_age_seconds=0,
            refresh_mode="live",
            next_refresh_at=NOW,
            metrics=OverviewRegimeMetrics(up_ratio=Decimal("55")),
            regime=OverviewRegimeAssessment(
                regime="轮动震荡",
                emotion_score=Decimal("55"),
                risk_score=Decimal("30"),
                heat_score=Decimal("50"),
                rotation_score=Decimal("62"),
                coverage_percent=Decimal("80"),
                market_coef=Decimal("0.5"),
                suitable_strategies=("0轴低吸模型",),
                avoid_strategies=("高开追涨",),
                reasons=("轮动分达到阈值",),
                missing_factors=("net_positive_ratio",),
                quality="partial",
            ),
            candidates=(),
            discipline="轮动震荡：只做前排低吸。",
            missing_data=("net_positive_ratio",),
            sources=("tdx-local-realtime",),
        )


def application(service: Service) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_quant_strategy_service] = lambda: service
    app.dependency_overrides[get_server_time] = lambda: NOW
    return app


def test_quant_strategy_route_returns_honest_partial_dashboard() -> None:
    service = Service()

    response = TestClient(application(service)).get(
        "/api/v1/a-shares/quant-strategy?limit=8&as_of=2026-07-30"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "partial"
    assert response.json()["regime"]["regime"] == "轮动震荡"
    assert response.json()["refresh_mode"] == "live"
    assert response.json()["data_age_seconds"] == 0
    assert service.calls == [(NOW, date(2026, 7, 30), 8)]


def test_quant_strategy_route_translates_source_failure() -> None:
    response = TestClient(application(Service(fail=True))).get(
        "/api/v1/a-shares/quant-strategy"
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "quant_strategy_unavailable"
