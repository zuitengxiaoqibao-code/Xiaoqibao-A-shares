from qibao_api.main import app


def test_main_registers_market_overview_route() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/a-shares/market-overview" in paths
    assert "/api/v1/a-shares/late-session-selection" in paths


def test_main_uses_the_yishu_product_title() -> None:
    assert app.title == "易数智算-A股观测台"
