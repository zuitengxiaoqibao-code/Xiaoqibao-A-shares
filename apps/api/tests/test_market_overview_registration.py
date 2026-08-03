from qibao_api.main import app


def test_main_registers_market_overview_route() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/a-shares/market-overview" in paths
